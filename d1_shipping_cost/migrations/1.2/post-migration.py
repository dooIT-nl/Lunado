"""Migrate Studio fields to native d1_ fields (idempotent).

Copies x_studio_use_qty → d1_use_qty, x_studio_use_length → d1_use_length on
product.template, and x_studio_qty → d1_qty, x_studio_length → d1_length on
sale.order.line.  Only where the source is filled and the destination is empty/zero.
The old x_studio fields are left untouched.
"""
import logging

_logger = logging.getLogger(__name__)


def _column_exists(cr, table, column):
    """Check if a column exists in the given table."""
    cr.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = %s AND column_name = %s",
        (table, column),
    )
    return bool(cr.fetchone())


def migrate(cr, version):
    _logger.info("d1_shipping_cost post-migration 1.2: migrating Studio fields")

    # --- product.template ---
    for src, dst in [
        ("x_studio_use_qty", "d1_use_qty"),
        ("x_studio_use_length", "d1_use_length"),
    ]:
        if not _column_exists(cr, "product_template", src):
            _logger.info("  Column %s does not exist on product_template — skipping.", src)
            continue
        if not _column_exists(cr, "product_template", dst):
            _logger.info("  Column %s does not exist on product_template — skipping.", dst)
            continue
        cr.execute(
            f"UPDATE product_template SET {dst} = {src} "
            f"WHERE {src} = True AND ({dst} IS NULL OR {dst} = False)"
        )
        _logger.info(
            "  product_template: %s → %s: %d rows updated.", src, dst, cr.rowcount
        )

    # --- sale.order.line ---
    for src, dst in [
        ("x_studio_qty", "d1_qty"),
        ("x_studio_length", "d1_length"),
    ]:
        if not _column_exists(cr, "sale_order_line", src):
            _logger.info("  Column %s does not exist on sale_order_line — skipping.", src)
            continue
        if not _column_exists(cr, "sale_order_line", dst):
            _logger.info("  Column %s does not exist on sale_order_line — skipping.", dst)
            continue
        cr.execute(
            f"UPDATE sale_order_line SET {dst} = {src} "
            f"WHERE {src} IS NOT NULL AND {src} != 0 "
            f"AND ({dst} IS NULL OR {dst} = 0)"
        )
        _logger.info(
            "  sale_order_line: %s → %s: %d rows updated.", src, dst, cr.rowcount
        )

    _logger.info("d1_shipping_cost post-migration 1.2: done.")
