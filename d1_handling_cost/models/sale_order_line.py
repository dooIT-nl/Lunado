import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # regelvelden die de handling-staffel kunnen beinvloeden
    _D1_HANDLING_LINE_TRIGGERS = {
        "product_id", "product_uom_qty", "price_unit", "discount",
    }

    @api.model_create_multi
    def create(self, vals_list):
        """Hersynchroniseer de handlingregel wanneer regels los worden
        toegevoegd (bv. via de API op een bestaande order)."""
        lines = super().create(vals_list)
        if not self.env.context.get("d1_skip_handling"):
            lines.order_id._d1_apply_handling()
        return lines

    def write(self, vals):
        """Hersynchroniseer de handlingregel wanneer bedragbepalende
        regelvelden wijzigen (het ordertotaal bepaalt de staffel)."""
        res = super().write(vals)
        if (
            not self.env.context.get("d1_skip_handling")
            and self._D1_HANDLING_LINE_TRIGGERS & vals.keys()
        ):
            self.order_id._d1_apply_handling()
        return res

    def unlink(self):
        """Hersynchroniseer de handlingregel na het verwijderen van regels
        (het ordertotaal kan in een andere staffel vallen)."""
        orders = self.order_id
        res = super().unlink()
        if not self.env.context.get("d1_skip_handling"):
            orders.exists()._d1_apply_handling()
        return res
