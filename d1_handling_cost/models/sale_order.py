import logging

from odoo import models
from odoo.fields import Command

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # ------------------------------------------------------------------
    # CRUD overrides — trigger handling sync
    # ------------------------------------------------------------------
    _D1_HANDLING_TRIGGER_FIELDS = {
        "partner_id", "order_line", "amount_untaxed", "amount_total", "state",
    }

    def write(self, vals):
        """Apply handling cost line when relevant fields change."""
        res = super().write(vals)
        if (
            not self.env.context.get("d1_skip_handling")
            and self._D1_HANDLING_TRIGGER_FIELDS & vals.keys()
        ):
            self.filtered(lambda o: o.state == "draft")._d1_apply_handling()
        return res

    # ------------------------------------------------------------------
    # Handling logic
    # ------------------------------------------------------------------
    def _d1_apply_handling(self):
        """Sync a single handling cost line on draft orders based on the
        customer's handling configuration and the order's net amount.

        Uses context flag ``d1_skip_handling`` to prevent recursion when
        writing the handling line back to the order.
        """
        if self.env.context.get("d1_skip_handling"):
            return
        for order in self:
            if order.state != "draft":
                continue

            handling = order.partner_id.d1_handling_id
            handling_product = handling.product_id

            # Find existing handling line on this order
            existing = order.order_line.filtered(
                lambda l, hp=handling_product: hp and l.product_template_id == hp
            )[:1]

            if not handling or not handling_product:
                if existing:
                    existing.unlink()
                continue

            # Calculate base amount excluding the handling product itself
            base_amount = sum(
                line.price_subtotal
                for line in order.order_line
                if line.product_template_id != handling_product
            )

            # Find the matching bracket
            bracket = self.env["d1.handling.line"].search(
                [
                    ("handling_id", "=", handling.id),
                    ("value_from", "<=", base_amount),
                    ("total", ">", base_amount),
                ],
                limit=1,
            )

            if bracket:
                if existing:
                    if existing.price_unit != bracket.amount:
                        existing.with_context(d1_skip_handling=True).write(
                            {"price_unit": bracket.amount}
                        )
                elif handling_product.product_variant_id:
                    order.with_context(d1_skip_handling=True).write({
                        "order_line": [
                            Command.create({
                                "product_id": handling_product.product_variant_id.id,
                                "product_uom_qty": 1,
                                "price_unit": bracket.amount,
                                "sequence": 99,
                            }),
                        ],
                    })
                else:
                    _logger.warning(
                        "d1_handling_cost: handling product %s has no variant; "
                        "skipping order %s",
                        handling_product.display_name,
                        order.name,
                    )
            elif existing:
                existing.unlink()
