"""Post-init hook: datamigratie + eindschoonmaak van de Studio-conversie.

Naast het bekende patroon (datakopie, automation-/veldopschoning) doet dit
sluitstuk-cluster de laatste veeg:
* KvK-nummer (x_studio_coc) migreert naar het standaardveld
  company_registry (besluit 17-09-2026);
* de Studio-automation 'Verkoop: Voeg Handling toe', het Handling-menu en
  de handmatige Handling-modellen (x_handling, x_handling_line_b0f2a)
  worden verwijderd (functioneel vervangen door d1_handling_cost);
* alle resterende studio_customization-views worden GEDEACTIVEERD (niet
  verwijderd) zodat de consultant ze op staging kan nalopen en eventueel
  gewenste lay-out alsnog als module-view kan (laten) porten.
"""
import logging

from lxml import etree

_logger = logging.getLogger(__name__)

MODULE = "d1_product_partner_data"

COLUMN_COPIES = [
    ("product_template", "x_studio_abc_code", "d1_abc_code",
     "x_studio_abc_code"),
    ("product_template", "x_studio_courant", "d1_courant",
     "x_studio_courant"),
    ("product_template", "x_studio_kostprijs_calc", "d1_cost_calc",
     "x_studio_kostprijs_calc"),
    ("sale_order", "x_studio_url_pakbon", "d1_delivery_note_url",
     "x_studio_url_pakbon"),
    # KvK-nummer naar het standaardveld; bestaande waarden niet overschrijven
    ("res_partner", "x_studio_coc", "company_registry", "x_studio_coc"),
]

REPLACED_AUTOMATIONS = [
    # functioneel vervangen door d1_handling_cost
    ("sale.order", "Verkoop: Voeg Handling toe"),
]

REPLACED_FIELDS = [
    ("product.template", "x_studio_abc_code"),
    ("product.template", "x_studio_courant"),
    ("product.template", "x_studio_available"),
    ("product.template", "x_studio_aantal_verpakkingen"),
    ("product.template", "x_studio_kostprijs_calc"),
    ("sale.order", "x_studio_url_pakbon"),
    ("res.partner", "x_studio_coc"),
    # data al gemigreerd door d1_handling_cost; veld zelf opruimen hoort hier
    ("res.partner", "x_studio_handling"),
]


def _column_exists(cr, table, column):
    """Controleer of een kolom bestaat (Studio-kolommen bestaan alleen op de
    productiedatabase)."""
    cr.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = %s AND column_name = %s",
        (table, column),
    )
    return bool(cr.fetchone())


def _copy_columns(env):
    """Kopieer data van de x_studio-kolommen naar de doelkolommen."""
    for table, src, dest, expr in COLUMN_COPIES:
        if not _column_exists(env.cr, table, src):
            _logger.info("%s: %s.%s not present, skipping", MODULE, table, src)
            continue
        if not _column_exists(env.cr, table, dest):
            _logger.warning("%s: target %s.%s not present, skipping",
                            MODULE, table, dest)
            continue
        # Alleen kolomnamen/expressies uit de vaste lijst hierboven.
        env.cr.execute(
            "UPDATE {table} SET {dest} = {expr} "
            "WHERE {src} IS NOT NULL AND ({dest} IS NULL "
            "OR {dest}::text = '')".format(
                table=table, dest=dest, expr=expr, src=src
            )
        )
        _logger.info("%s: copied %s.%s -> %s (%s rows)",
                     MODULE, table, src, dest, env.cr.rowcount)


def _remove_replaced_automations(env):
    """Verwijder de vervangen Studio-automations inclusief server-acties."""
    for model_name, name in REPLACED_AUTOMATIONS:
        autos = env["base.automation"].search(
            [
                ("model_id.model", "=", model_name),
                ("name", "=", name),
                "|", ("active", "=", True), ("active", "=", False),
            ]
        )
        if not autos:
            continue
        actions = autos.action_server_ids
        autos.unlink()
        try:
            actions.unlink()
        except Exception:
            _logger.warning("%s: could not remove server action(s) %s",
                            MODULE, actions.mapped("name"), exc_info=True)
        _logger.info("%s: removed automation '%s' (%s)", MODULE, name,
                     model_name)


def _strip_field_from_studio_views(env, model_name, field_name):
    """Verwijder veld-verwijzingen uit Studio-views zodat die geldig blijven
    nadat het veld is verwijderd. Blijft het veld ergens in attributen of
    xpath-expressies staan (niet schoon te knippen), dan wordt de hele
    Studio-view gedeactiveerd."""
    # BEWUST geen modelfilter: regelvelden staan embedded in views van het
    # oudermodel (orderregels in de sale.order-form, moves in de
    # stock.picking-form) — Odoo's verwijdercheck valideert al die views.
    views = env["ir.ui.view"].search([("arch_db", "like", field_name)])
    for view in views:
        xml_id = view.get_external_id().get(view.id) or ""
        if not xml_id.startswith("studio_customization."):
            continue
        try:
            arch = etree.fromstring(view.arch_db.encode("utf-8"))
            nodes = arch.xpath(
                "//field[@name='%s'] | //label[@for='%s'] "
                "| //xpath[contains(@expr, '%s')]"
                % (field_name, field_name, field_name)
            )
            for node in nodes:
                node.getparent().remove(node)
            new_arch = etree.tostring(arch, encoding="unicode")
            if field_name in new_arch:
                view.active = False
                _logger.info(
                    "%s: view %s still references %s in attributes; "
                    "deactivated the view", MODULE, xml_id, field_name)
            elif nodes:
                view.arch_db = new_arch
                _logger.info("%s: stripped %s from view %s",
                             MODULE, field_name, xml_id)
        except Exception:
            _logger.warning(
                "%s: could not strip %s from view %s; deactivating view",
                MODULE, field_name, xml_id, exc_info=True)
            view.active = False


def _remove_replaced_fields(env):
    """Verwijder de vervangen handmatige Studio-velden (na de datakopie).

    Meerdere passes: afhankelijkheidsketens (bv. een related veld op
    stock.move dat naar de orderregel wijst) blokkeren de eerste poging maar
    lossen op zodra de afhankelijke velden weg zijn. Definitief mislukte
    velden worden zonder traceback gelogd (schoon buildlog) en kunnen
    handmatig worden opgeruimd; de installatie blokkeert nooit.
    """
    remaining = list(REPLACED_FIELDS)
    failures = []
    for _pass in range(4):
        failures = []
        for model_name, field_name in remaining:
            field = env["ir.model.fields"].search(
                [
                    ("model", "=", model_name),
                    ("name", "=", field_name),
                    ("state", "=", "manual"),
                ]
            )
            if not field:
                continue
            _strip_field_from_studio_views(env, model_name, field_name)
            try:
                field.unlink()
                _logger.info("%s: removed studio field %s.%s",
                             MODULE, model_name, field_name)
            except Exception as exc:
                failures.append((model_name, field_name, str(exc)))
        if not failures:
            return
        remaining = [(m, f) for m, f, _ in failures]
    for model_name, field_name, reason in failures:
        _logger.warning(
            "%s: could not remove studio field %s.%s after multiple passes "
            "(%s); please clean up manually",
            MODULE, model_name, field_name, reason)


def _remove_stale_studio_field_rows(env):
    """Verwijder wees-metadata van x_studio-velden: ir.model.fields-rijen
    zonder bijbehorend veld in het register.

    Achtergrond: product.product en res.users erven via _inherits van
    product.template en res.partner. Voor elk Studio-veld op het oudermodel
    maakt Odoo automatisch een gedelegeerd veld (state 'base') op het
    kindmodel aan. Bij het verwijderen van het handmatige ouderveld verdwijnt
    de delegatie uit het register, maar de metadata-rij blijft staan:
    'base'-rijen worden alleen opgeruimd bij een update van de eigenaar-module
    en die is er voor deze rijen niet. Ze zijn via de UI niet te verwijderen
    (basisveld) en vervuilen de veldenlijst en toekomstige upgrades.

    Criterium — bewust NIET via het register (tijdens het laden/migreren is
    het register nog niet compleet; modules die later laden, zoals
    d1_studio_compat, lijken dan ten onrechte afwezig): een gedelegeerde rij
    op het kindmodel is wees zodra er geen veldrij met dezelfde naam meer op
    het oudermodel bestaat. Dat is puur in de database te bepalen en dus
    onafhankelijk van de laadvolgorde.

    Veiligheidsregels:
    * alleen de _inherits-kindmodellen (product.product, res.users) worden
      geveegd; velden op andere modellen blijven ongemoeid (aliassen van
      d1_studio_compat leven op de oudermodellen en hun delegaties op de
      kindmodellen hebben een ouderrij — beide blijven staan);
    * alleen state 'base' (delegaties); handmatige velden lopen via
      _remove_replaced_fields;
    * velden van de handmatige x_handling-modellen verdwijnen samen met het
      model (zie _remove_handling_models) en blijven hier buiten schot.
    """
    # SQL i.p.v. ORM: ir.model.fields.unlink() weigert 'base'-rijen, en er
    # valt hier niets anders op te ruimen dan de metadata zelf (geen kolom,
    # geen registerveld). Geen gebruikersinvoer in de query.
    delegations = [
        ("product.product", "product.template"),
        ("res.users", "res.partner"),
    ]
    removed = []
    for child, parent in delegations:
        env.cr.execute(
            r"SELECT f.id, f.name FROM ir_model_fields f "
            r"WHERE f.model = %s AND f.name LIKE 'x\_studio\_%%' "
            r"AND f.state = 'base' "
            r"AND NOT EXISTS (SELECT 1 FROM ir_model_fields p "
            r"                WHERE p.model = %s AND p.name = f.name) "
            r"ORDER BY f.name",
            (child, parent),
        )
        for field_id, field_name in env.cr.fetchall():
            try:
                with env.cr.savepoint():
                    env.cr.execute(
                        "DELETE FROM ir_model_data "
                        "WHERE model = 'ir.model.fields' AND res_id = %s",
                        (field_id,))
                    env.cr.execute(
                        "DELETE FROM ir_model_fields WHERE id = %s",
                        (field_id,))
                removed.append("%s.%s" % (child, field_name))
            except Exception as exc:
                _logger.warning(
                    "%s: could not remove stale field row %s.%s (%s); "
                    "please clean up manually",
                    MODULE, child, field_name, exc)
    if removed:
        env["ir.model.fields"].invalidate_model()
        env.registry.clear_cache()
        _logger.info("%s: removed %s stale x_studio field row(s): %s",
                     MODULE, len(removed), ", ".join(removed))


def _remove_handling_menu(env):
    """Verwijder het Studio-menu en de vensteractie van Handling (vervangen
    door d1_handling_cost)."""
    imds = env["ir.model.data"].search(
        [
            ("module", "=", "studio_customization"),
            ("model", "in", ("ir.ui.menu", "ir.actions.act_window")),
        ]
    )
    # eerst verzamelen: unlink van het doelrecord verwijdert (cascade) ook
    # het ir.model.data-record zelf
    targets = [(imd.model, imd.res_id) for imd in imds]
    for model_name, res_id in targets:
        record = env[model_name].browse(res_id).exists()
        if not record:
            continue
        try:
            name = record.display_name
            record.unlink()
            _logger.info("%s: removed studio %s '%s'", MODULE, model_name,
                         name)
        except Exception:
            _logger.warning("%s: could not remove studio %s (id %s)",
                            MODULE, model_name, res_id, exc_info=True)


# handmatige Studio-modellen van de oude Handling-matrix (vervangen door
# d1_handling_cost); de regels eerst — die verwijzen met een m2o naar
# x_handling
HANDLING_MODELS = ("x_handling_line_b0f2a", "x_handling")


def _remove_handling_models(env, model_names=HANDLING_MODELS):
    """Verwijder de handmatige Studio-modellen van de oude Handling-matrix.

    De data is al gemigreerd door d1_handling_cost; het menu en de automation
    zijn eerder in deze hook opgeruimd. Unlink van het ir.model-record
    verwijdert (cascade) ook de velden, toegangsregels en de databasetabel;
    views op het model gaan eerst. Besluit 25-09-2026: de handmatige
    verwijderstap na verificatie (deploy-checklist stap 9) vervalt hiermee.
    """
    for model_name in model_names:
        model = env["ir.model"].search(
            [("model", "=", model_name), ("state", "=", "manual")]
        )
        if not model:
            continue
        try:
            with env.cr.savepoint():
                views = env["ir.ui.view"].with_context(
                    active_test=False
                ).search([("model", "=", model_name)])
                view_count = len(views)
                views.unlink()
                # aantal datarijen loggen vóór de tabel (cascade) verdwijnt;
                # tabelnaam komt uit de vaste lijst hierboven
                table = model_name.replace(".", "_")
                env.cr.execute('SELECT COUNT(*) FROM "%s"' % table)
                row_count = env.cr.fetchone()[0]
                model.unlink()
            _logger.info(
                "%s: removed studio model %s (%s view(s), %s data row(s))",
                MODULE, model_name, view_count, row_count,
            )
        except Exception as exc:
            _logger.warning(
                "%s: could not remove studio model %s (%s); "
                "please clean up manually", MODULE, model_name, exc,
            )


def _deactivate_remaining_studio_views(env):
    """Deactiveer alle resterende studio_customization-views (eindschoonmaak;
    bewust niet verwijderen zodat gewenste lay-out op staging nog te
    beoordelen is)."""
    imds = env["ir.model.data"].search(
        [
            ("module", "=", "studio_customization"),
            ("model", "=", "ir.ui.view"),
        ]
    )
    views = env["ir.ui.view"].browse(imds.mapped("res_id")).exists()
    active_views = views.filtered("active")
    if active_views:
        active_views.write({"active": False})
        _logger.info(
            "%s: deactivated %s remaining studio views: %s",
            MODULE, len(active_views), active_views.mapped("name"),
        )


def post_init_hook(env):
    """Migreer Studio-data en voer de eindschoonmaak van de conversie uit."""
    _copy_columns(env)
    _remove_replaced_automations(env)
    _remove_replaced_fields(env)
    _remove_stale_studio_field_rows(env)
    _remove_handling_menu(env)
    _remove_handling_models(env)
    _deactivate_remaining_studio_views(env)
