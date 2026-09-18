"""Post-init hook: datamigratie vanuit Studio-velden + opschoning.

Zelfde patroon als d1_sale_order_checks/d1_sale_dropshipment. Extra stap:
het vinkje 'Geen leverdefaults van leverancier' wordt automatisch gezet op
het Dropship-operatietype (vervangt de hardcoded uitsluiting van id 10 in
het domein van de Studio-automation).
"""
import logging

from lxml import etree

_logger = logging.getLogger(__name__)

MODULE = "d1_purchase_partner_delivery"

COLUMN_COPIES = [
    ("res_partner", "x_studio_type_levering", "d1_delivery_picking_type_id",
     "x_studio_type_levering"),
    ("res_partner", "x_studio_incoterm_id", "d1_incoterm_id",
     "x_studio_incoterm_id"),
]

REPLACED_AUTOMATIONS = [
    ("purchase.order", "Vul Leveren aan en Leverconditie"),
]

REPLACED_FIELDS = [
    ("res.partner", "x_studio_type_levering"),
    ("res.partner", "x_studio_incoterm_id"),
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
    """Kopieer data van de x_studio-kolommen naar de nieuwe d1_-kolommen."""
    for table, src, dest, expr in COLUMN_COPIES:
        if not _column_exists(env.cr, table, src):
            _logger.info("%s: %s.%s not present, skipping", MODULE, table, src)
            continue
        # Alleen kolomnamen/expressies uit de vaste lijst hierboven.
        env.cr.execute(
            "UPDATE {table} SET {dest} = {expr} "
            "WHERE {src} IS NOT NULL AND {dest} IS NULL".format(
                table=table, dest=dest, expr=expr, src=src
            )
        )
        _logger.info("%s: copied %s.%s -> %s (%s rows)",
                     MODULE, table, src, dest, env.cr.rowcount)


def _flag_dropship_picking_type(env):
    """Zet het uitsluitingsvinkje op het Dropship-operatietype (indien de
    dropshipping-module is geinstalleerd)."""
    dropship = env.ref(
        "stock_dropshipping.picking_type_dropship", raise_if_not_found=False
    )
    if dropship:
        dropship.d1_no_partner_delivery_default = True
        _logger.info("%s: flagged '%s' as excluded from partner delivery "
                     "defaults", MODULE, dropship.display_name)
    else:
        _logger.info("%s: dropship picking type not found; configure the "
                     "exclusion flag manually if needed", MODULE)


def _remove_replaced_automations(env):
    """Verwijder de vervangen Studio-automation inclusief server-acties."""
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
    views = env["ir.ui.view"].search(
        [("model", "=", model_name), ("arch_db", "like", field_name)]
    )
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


def post_init_hook(env):
    """Migreer Studio-data, zet de Dropship-uitsluiting en schoon
    Studio-restanten op."""
    _copy_columns(env)
    _flag_dropship_picking_type(env)
    _remove_replaced_automations(env)
    _remove_replaced_fields(env)
