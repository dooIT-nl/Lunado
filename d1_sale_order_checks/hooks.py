"""Post-init hook: datamigratie vanuit Studio-velden + opschoning.

Draait veilig op elke database:
* op een verse (dev/test-)database bestaan de x_studio-kolommen niet en
  worden alle stappen overgeslagen;
* op de productiedatabase wordt de data gekopieerd naar de nieuwe
  d1_-velden en worden de vervangen Studio-automations, -velden en
  view-verwijzingen opgeruimd.
"""
import logging

from lxml import etree

_logger = logging.getLogger(__name__)

# (tabel, bronkolom) -> (doelkolom, SQL-expressie voor de waarde)
COLUMN_COPIES = [
    ("res_partner", "x_studio_verzekerd_bedrag", "d1_insured_amount",
     "x_studio_verzekerd_bedrag"),
    ("res_partner", "x_studio_rel_type", "d1_rel_type",
     "CASE x_studio_rel_type WHEN 'Prospect' THEN 'prospect' "
     "WHEN 'Klant' THEN 'customer' ELSE NULL END"),
    ("res_partner", "x_studio_kredietverzekering", "d1_credit_insurance",
     "CASE x_studio_kredietverzekering "
     "WHEN 'Verzekerd, eigen beoordeling' THEN 'insured_own' "
     "WHEN 'Verzekerd, beoordeling verzekeraar' THEN 'insured_insurer' "
     "WHEN 'Niet verzekerd' THEN 'not_insured' ELSE NULL END"),
    ("sale_order", "x_studio_exceed_credit_limit", "d1_exceed_credit_limit",
     "x_studio_exceed_credit_limit"),
]

# vervangen Studio-automations: (model, naam)
REPLACED_AUTOMATIONS = [
    ("sale.order", "Kredietlimiet"),
    ("sale.order", "Relatie is Prospect"),
    ("sale.order", "Verkooporder: Dubbele referentie"),
]

# vervangen Studio-velden: (model, veldnaam)
REPLACED_FIELDS = [
    ("res.partner", "x_studio_rel_type"),
    ("res.partner", "x_studio_kredietverzekering"),
    ("res.partner", "x_studio_verzekerd_bedrag"),
    ("sale.order", "x_studio_credit_limit_exceeded"),
    ("sale.order", "x_studio_exceed_credit_limit"),
]


def _column_exists(cr, table, column):
    """Controleer of een kolom bestaat (bron-Studio-kolommen bestaan alleen
    op de productiedatabase)."""
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
            _logger.info("d1_sale_order_checks: %s.%s not present, skipping",
                         table, src)
            continue
        # Alleen kolomnamen/expressies uit de vaste lijst hierboven; geen
        # gebruikersinvoer in de query.
        env.cr.execute(
            "UPDATE {table} SET {dest} = {expr} "
            "WHERE {src} IS NOT NULL AND {dest} IS NULL".format(
                table=table, dest=dest, expr=expr, src=src
            )
        )
        _logger.info(
            "d1_sale_order_checks: copied %s.%s -> %s (%s rows)",
            table, src, dest, env.cr.rowcount,
        )


def _remove_replaced_automations(env):
    """Verwijder de vervangen Studio-automations inclusief hun
    server-acties."""
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
            _logger.warning(
                "d1_sale_order_checks: could not remove server action(s) %s",
                actions.mapped("name"), exc_info=True,
            )
        _logger.info(
            "d1_sale_order_checks: removed automation '%s' (%s)", name,
            model_name,
        )


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
                    "deactivated the view", "d1_sale_order_checks", xml_id, field_name)
            elif nodes:
                view.arch_db = new_arch
                _logger.info("%s: stripped %s from view %s",
                             "d1_sale_order_checks", field_name, xml_id)
        except Exception:
            _logger.warning(
                "%s: could not strip %s from view %s; deactivating view",
                "d1_sale_order_checks", field_name, xml_id, exc_info=True)
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
                             "d1_sale_order_checks", model_name, field_name)
            except Exception as exc:
                failures.append((model_name, field_name, str(exc)))
        if not failures:
            return
        remaining = [(m, f) for m, f, _ in failures]
    for model_name, field_name, reason in failures:
        _logger.warning(
            "%s: could not remove studio field %s.%s after multiple passes "
            "(%s); please clean up manually",
            "d1_sale_order_checks", model_name, field_name, reason)


def post_init_hook(env):
    """Migreer Studio-data naar de d1_-velden en schoon Studio-restanten op."""
    _copy_columns(env)
    _remove_replaced_automations(env)
    _remove_replaced_fields(env)
