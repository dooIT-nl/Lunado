"""Override nl_NL translation for product_uom_qty on sale.order.line.

The standard sale module translates 'Quantity' as 'Hoeveelheid'.
We override it to 'Aantal' to distinguish from d1_qty ('Hoeveelheid').
PO-based override doesn't work for cross-module field translations,
so we set the JSONB value directly.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info(
        "d1_shipping_cost post-migration 1.5: "
        "override product_uom_qty nl_NL → 'Aantal'"
    )
    cr.execute("""
        UPDATE ir_model_fields
        SET field_description = jsonb_set(
            field_description, '{nl_NL}', '"Aantal"'
        )
        WHERE model = 'sale.order.line'
          AND name = 'product_uom_qty'
          AND field_description ? 'nl_NL'
    """)
    _logger.info("  Updated %d rows.", cr.rowcount)
