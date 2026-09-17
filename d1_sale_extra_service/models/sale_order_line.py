import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.model_create_multi
    def create(self, vals_list):
        """Synchroniseer de dienstregels na het toevoegen van regels."""
        lines = super().create(vals_list)
        if not self.env.context.get("d1_skip_extra_service"):
            lines.order_id._d1_sync_extra_service_lines()
        return lines

    def write(self, vals):
        """Synchroniseer de dienstregels wanneer de zaaghoeveelheid of het
        product wijzigt (pariteit met de trigger van de Studio-automation)."""
        res = super().write(vals)
        if not self.env.context.get("d1_skip_extra_service") and (
            "d1_qty" in vals or "product_id" in vals
        ):
            self.order_id._d1_sync_extra_service_lines()
        return res
