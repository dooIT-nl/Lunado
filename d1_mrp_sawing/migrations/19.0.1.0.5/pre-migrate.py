"""Hernoem d1_sawn_product_id naar d1_raw_product_id (CIS20260922).

Draait vóór het laden van de module, zodat de nieuwe velddefinitie de
bestaande (hernoemde) kolom aantreft en de data behouden blijft. Guards
maken de migratie idempotent: op een database zonder de oude kolom (verse
installatie) gebeurt er niets.
"""
import logging

_logger = logging.getLogger(__name__)

OLD = "d1_sawn_product_id"
NEW = "d1_raw_product_id"


def _column_exists(cr, table, column):
    cr.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = %s AND column_name = %s",
        (table, column),
    )
    return bool(cr.fetchone())


def migrate(cr, version):
    """Hernoem de databasekolom en de reflectie-records van het veld."""
    if not _column_exists(cr, "product_template", OLD):
        _logger.info("d1_mrp_sawing: column %s not present, skipping rename",
                     OLD)
        return
    if _column_exists(cr, "product_template", NEW):
        _logger.warning(
            "d1_mrp_sawing: both %s and %s exist; copying values into %s "
            "where empty instead of renaming", OLD, NEW, NEW)
        cr.execute(
            "UPDATE product_template SET d1_raw_product_id = "
            "d1_sawn_product_id WHERE d1_sawn_product_id IS NOT NULL "
            "AND d1_raw_product_id IS NULL"
        )
        return
    cr.execute(
        "ALTER TABLE product_template RENAME COLUMN d1_sawn_product_id "
        "TO d1_raw_product_id"
    )
    cr.execute(
        "UPDATE ir_model_fields SET name = %s "
        "WHERE model = 'product.template' AND name = %s",
        (NEW, OLD),
    )
    cr.execute(
        "UPDATE ir_model_data SET name = %s "
        "WHERE model = 'ir.model.fields' AND name = %s",
        ("field_product_template__" + NEW, "field_product_template__" + OLD),
    )
    _logger.info("d1_mrp_sawing: renamed %s to %s (CIS20260922)", OLD, NEW)
