"""Post-init hook: datamigratie vanuit Studio-velden + opschoning.

Zelfde patroon als de overige conversie-modules. Extra: ir.default-waarden
voor zaagcapaciteit/zaagtijd worden overgezet naar de nieuwe velden.
"""
import json
import logging

from lxml import etree

_logger = logging.getLogger(__name__)

MODULE = "d1_mrp_sawing"

COLUMN_COPIES = [
    ("product_template", "x_studio_use_qty", "d1_use_qty", "x_studio_use_qty"),
    ("product_template", "x_studio_use_length", "d1_use_length",
     "x_studio_use_length"),
    ("product_template", "x_studio_zaagcap_bew", "d1_saw_capacity",
     "x_studio_zaagcap_bew"),
    ("product_template", "x_studio_zaagtijd_per_bew", "d1_saw_time",
     "x_studio_zaagtijd_per_bew"),
    ("product_template", "x_studio_artikelcode_gezaagd", "d1_raw_product_id",
     "x_studio_artikelcode_gezaagd"),
    ("product_template", "x_studio_framecalculator_janee", "d1_framecalculator",
     "x_studio_framecalculator_janee"),
    ("sale_order_line", "x_studio_qty", "d1_qty", "x_studio_qty"),
    ("sale_order_line", "x_studio_length", "d1_length", "x_studio_length"),
    ("sale_order_line", "x_studio_weight", "d1_weight", "x_studio_weight"),
    ("sale_order_line", "x_studio_frame_id", "d1_frame_id",
     "x_studio_frame_id"),
    ("sale_order_line", "x_studio_frame_nr", "d1_frame_nr",
     "x_studio_frame_nr"),
    ("sale_order_line", "x_studio_qty_var_name", "d1_qty_var_name",
     "x_studio_qty_var_name"),
]

# ir.default-waarden overzetten: (model, oud veld, nieuw veld)
DEFAULT_COPIES = [
    ("product.template", "x_studio_zaagcap_bew", "d1_saw_capacity"),
    ("product.template", "x_studio_zaagtijd_per_bew", "d1_saw_time"),
]

REPLACED_AUTOMATIONS = [
    ("product.template", "Controle Product - Lengte"),
    ("product.template", "Zaagcap bew >0"),
    ("product.template", "Zaagtijd per bew>0"),
    ("sale.order.line", "Sales Order Line - Qty"),
    ("sale.order.line", "Vul lengte in verkooporderregel"),
    ("mrp.workorder", "Werkorder: Duur vullen"),
    ("mrp.workorder", "Werkorder: Verwachte duur vullen"),
]

REPLACED_FIELDS = [
    ("product.template", "x_studio_use_qty"),
    ("product.template", "x_studio_use_length"),
    ("product.template", "x_studio_zaagcap_bew"),
    ("product.template", "x_studio_zaagtijd_per_bew"),
    ("product.template", "x_studio_artikelcode_gezaagd"),
    ("product.template", "x_studio_framecalculator_janee"),
    ("sale.order.line", "x_studio_qty"),
    ("sale.order.line", "x_studio_length"),
    ("sale.order.line", "x_studio_use_qty"),
    ("sale.order.line", "x_studio_use_length"),
    ("sale.order.line", "x_studio_weight"),
    ("sale.order.line", "x_studio_frame_id"),
    ("sale.order.line", "x_studio_frame_nr"),
    ("sale.order.line", "x_studio_qty_var_name"),
    ("mrp.production", "x_studio_qty"),
    ("mrp.production", "x_studio_length"),
    ("mrp.production", "x_studio_frame_nr"),
    ("mrp.production", "x_studio_productietijd"),
    ("mrp.workorder", "x_studio_qty"),
    ("mrp.workorder", "x_studio_length"),
    ("mrp.workorder", "x_studio_productietijd_eindproduct"),
    ("stock.move", "x_studio_qty"),
    ("stock.move", "x_studio_length"),
    ("stock.move", "x_studio_productietijd_eindproduct"),
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


def _copy_defaults(env):
    """Zet ir.default-waarden van de oude Studio-velden over naar de nieuwe
    velden (alleen bedrijfs-/gebruikersonafhankelijke defaults)."""
    for model_name, src_field, dest_field in DEFAULT_COPIES:
        field = env["ir.model.fields"].search(
            [("model", "=", model_name), ("name", "=", src_field)], limit=1
        )
        if not field:
            continue
        defaults = env["ir.default"].search(
            [("field_id", "=", field.id), ("user_id", "=", False),
             ("company_id", "=", False)]
        )
        for default in defaults:
            try:
                value = json.loads(default.json_value)
            except (ValueError, TypeError):
                _logger.warning("%s: could not parse default %r for %s.%s",
                                MODULE, default.json_value, model_name,
                                src_field)
                continue
            env["ir.default"].set(model_name, dest_field, value)
            _logger.info("%s: copied default %s for %s.%s -> %s",
                         MODULE, value, model_name, src_field, dest_field)


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
    """Migreer Studio-data (incl. defaults) en schoon Studio-restanten op."""
    _copy_columns(env)
    _copy_defaults(env)
    _remove_replaced_automations(env)
    _remove_replaced_fields(env)
