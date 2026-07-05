import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    d1_qty = fields.Float(
        string="Hoeveelheid",
        copy=True,
        help="Aantal stuks voor de hoeveelheid × lengte berekening.",
    )
    d1_length_cm = fields.Float(
        string="Lengte",
        copy=True,
        help="Lengte in cm voor de hoeveelheid × lengte berekening. "
             "Wordt automatisch gevuld vanuit het product als 'Gebruik Lengte' uit staat.",
    )

    # Related fields for read-only logic in the view
    d1_use_qty = fields.Boolean(
        related="product_template_id.d1_use_qty",
        readonly=True,
    )
    d1_use_length = fields.Boolean(
        related="product_template_id.d1_use_length",
        readonly=True,
    )

    # ------------------------------------------------------------------
    # Shared helper: qty × length calculation
    # ------------------------------------------------------------------

    def _d1_apply_qty_length(self):
        """Fill line length from product and recalculate product_uom_qty.

        - If product d1_use_qty=True and d1_use_length=False:
          d1_length_cm = product.d1_length_cm (auto-fill from product).
        - If product d1_use_qty=True:
          product_uom_qty = d1_qty * d1_length_cm.
        Products without d1_use_qty are left untouched (normal manual qty).
        """
        for line in self:
            tmpl = line.product_template_id
            if not tmpl or not tmpl.d1_use_qty:
                continue
            if not tmpl.d1_use_length:
                # Product stores length in cm; order line uses meters
                line.d1_length_cm = (tmpl.d1_length_cm or 0.0) / 100.0
            line.product_uom_qty = (line.d1_qty or 0.0) * (line.d1_length_cm or 0.0)

    # ------------------------------------------------------------------
    # Onchange (UI) — fires in-memory, no persist, no recursion
    # ------------------------------------------------------------------

    @api.onchange("product_id", "product_template_id", "d1_qty", "d1_length_cm")
    def _d1_onchange_qty_length(self):
        """Recalculate qty × length when relevant fields change in the UI."""
        self._d1_apply_qty_length()

    # ------------------------------------------------------------------
    # Create / Write (API + UI persist)
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        """Apply qty × length calculation after creating lines (API path)."""
        lines = super().create(vals_list)
        lines.with_context(d1_skip_qty_length=True)._d1_apply_qty_length()
        return lines

    def write(self, vals):
        """Apply qty × length calculation after writing trigger fields."""
        res = super().write(vals)
        trigger = {"product_id", "product_template_id", "d1_qty", "d1_length_cm"}
        if trigger & set(vals) and not self.env.context.get("d1_skip_qty_length"):
            self.with_context(d1_skip_qty_length=True)._d1_apply_qty_length()
        return res
