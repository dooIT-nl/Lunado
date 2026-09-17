"""Post-init hook: datamigratie vanuit Studio-velden + opschoning.

Zelfde patroon als de overige conversie-modules.
"""
import logging

from lxml import etree

_logger = logging.getLogger(__name__)

MODULE = "d1_sale_extra_service"

COLUMN_COPIES = [
    ("product_category", "x_studio_extra_dienst",
     "d1_extra_service_product_id", "x_studio_extra_dienst"),
]

# match op 'ilike' zodat kleine naamafwijkingen (spaties, hoofdletters)
# de opschoning niet laten missen — bleek op staging het geval
REPLACED_AUTOMATIONS = [
    ("sale.order.line", "Voeg dienst toe"),
]

REPLACED_FIELDS = [
    ("product.category", "x_studio_extra_dienst"),
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


def _remove_replaced_automations(env):
    """Verwijder de vervangen Studio-automation inclusief server-acties."""
    for model_name, name in REPLACED_AUTOMATIONS:
        autos = env["base.automation"].search(
            [
                ("model_id.model", "=", model_name),
                ("name", "ilike", name),
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
    nadat het veld is verwijderd."""
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
                "//field[@name='%s'] | //label[@for='%s']"
                % (field_name, field_name)
            )
            if not nodes:
                continue
            for node in nodes:
                node.getparent().remove(node)
            view.arch_db = etree.tostring(arch, encoding="unicode")
            _logger.info("%s: stripped %s from view %s",
                         MODULE, field_name, xml_id)
        except Exception:
            _logger.warning(
                "%s: could not strip %s from view %s; deactivating view",
                MODULE, field_name, xml_id, exc_info=True)
            view.active = False


def _remove_replaced_fields(env):
    """Verwijder de vervangen handmatige Studio-velden (na de datakopie);
    fouten worden gelogd en overgeslagen zodat de installatie nooit
    blokkeert."""
    for model_name, field_name in REPLACED_FIELDS:
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
        except Exception:
            _logger.warning(
                "%s: could not remove studio field %s.%s (still "
                "referenced?); please clean up manually",
                MODULE, model_name, field_name, exc_info=True)


def post_init_hook(env):
    """Migreer Studio-data naar de d1_-velden en schoon Studio-restanten op."""
    _copy_columns(env)
    _remove_replaced_automations(env)
    _remove_replaced_fields(env)
