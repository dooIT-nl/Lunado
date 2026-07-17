"""Rename column d1_length_cm → d1_length on sale_order_line.

Pre-migration so the ORM finds the column under the new name when the
module loads.  Idempotent: skips if the old column does not exist or the
new column already exists.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info("d1_shipping_cost pre-migration 1.3: rename d1_length_cm → d1_length")

    # Check if old column exists
    cr.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'sale_order_line' AND column_name = 'd1_length_cm'"
    )
    if not cr.fetchone():
        _logger.info("  Column d1_length_cm does not exist — nothing to rename.")
        return

    # Check if new column already exists (avoid conflict)
    cr.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'sale_order_line' AND column_name = 'd1_length'"
    )
    if cr.fetchone():
        _logger.info("  Column d1_length already exists — skipping rename.")
        return

    cr.execute("ALTER TABLE sale_order_line RENAME COLUMN d1_length_cm TO d1_length")
    _logger.info("  Renamed sale_order_line.d1_length_cm → d1_length.")

    # Also update ir_model_fields so the ORM doesn't try to recreate
    cr.execute(
        "UPDATE ir_model_fields SET name = 'd1_length' "
        "WHERE model = 'sale.order.line' AND name = 'd1_length_cm'"
    )
    _logger.info("  Updated ir_model_fields: %d rows.", cr.rowcount)

    _logger.info("d1_shipping_cost pre-migration 1.3: done.")
