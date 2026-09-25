"""Post-init hook: datamigratie vanuit Studio-velden + opschoning.

Zelfde patroon als de overige conversie-modules. Extra stap: de combi-route
per magazijn wordt gevuld volgens de mapping uit de oude Studio-automation
(magazijn 1/Rotterdam -> route 21/Combi RTM, magazijn 2/Wesseling ->
route 22/Combi WLS) — met naam-controle als vangnet, zodat er nooit een
verkeerde route wordt gekoppeld op een database met andere ids.
"""
import logging

from lxml import etree

_logger = logging.getLogger(__name__)

MODULE = "d1_sale_combi"

COLUMN_COPIES = [
    ("product_template", "x_studio_default_warehouse_id",
     "d1_default_warehouse_id", "x_studio_default_warehouse_id"),
    ("sale_order", "x_studio_combi", "d1_combi", "x_studio_combi"),
]

# mapping uit de oude automation: warehouse-id -> route-id (productie-ids,
# bevestigd door de klant op 17-09-2026)
COMBI_ROUTE_MAPPING = {1: 21, 2: 22}

REPLACED_AUTOMATIONS = [
    ("sale.order", "Verkooporder: Combi order"),
    ("sale.order.line", "Verkooporderregel: Combi order"),
]

REPLACED_FIELDS = [
    ("sale.order", "x_studio_combi"),
    ("product.template", "x_studio_default_warehouse_id"),
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


def _configure_combi_routes(env):
    """Vul het veld Combi Route per magazijn volgens de oude mapping.

    Vangnet: de route wordt alleen gekoppeld als beide records bestaan en de
    routenaam 'combi' bevat — op databases met andere ids (dev/staging na
    rebuild) gebeurt er niets en wordt dit gelogd.
    """
    for wh_id, route_id in COMBI_ROUTE_MAPPING.items():
        warehouse = env["stock.warehouse"].browse(wh_id).exists()
        route = env["stock.route"].browse(route_id).exists()
        if not warehouse or not route:
            _logger.info(
                "%s: warehouse %s / route %s not found; configure the combi "
                "route manually if needed", MODULE, wh_id, route_id)
            continue
        if "combi" not in (route.name or "").lower():
            _logger.warning(
                "%s: route %s (%s) does not look like a combi route; "
                "skipping automatic mapping for warehouse %s",
                MODULE, route_id, route.name, warehouse.display_name)
            continue
        if not warehouse.d1_combi_route_id:
            warehouse.d1_combi_route_id = route
            _logger.info("%s: combi route '%s' set on warehouse '%s'",
                         MODULE, route.name, warehouse.display_name)


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


def post_init_hook(env):
    """Migreer Studio-data, configureer de combi-routes en schoon
    Studio-restanten op."""
    _copy_columns(env)
    _configure_combi_routes(env)
    _remove_replaced_automations(env)
    _remove_replaced_fields(env)
