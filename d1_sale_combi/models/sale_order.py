import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    d1_combi = fields.Boolean(
        string="Combi",
        copy=False,
        help="Combi order: lines whose product has a different default "
        "warehouse than the order warehouse are routed via the combi route "
        "of the order warehouse.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Pas de combi-routering toe bij aanmaken (dekt ook API-creates)."""
        orders = super().create(vals_list)
        orders._d1_apply_combi_routes()
        return orders

    def write(self, vals):
        """Pas de combi-routering opnieuw toe wanneer de combi-vlag of het
        magazijn wijzigt."""
        res = super().write(vals)
        if "d1_combi" in vals or "warehouse_id" in vals:
            self._d1_apply_combi_routes()
        return res

    def _d1_apply_combi_routes(self):
        """Routeer alle regels van combi-orders (offerte-status) via de
        combi-route van het ordermagazijn. Zie sale.order.line voor de
        regel-logica en foutcondities."""
        for order in self:
            if not order.d1_combi or order.state not in ("draft", "sent"):
                continue
            order.order_line._d1_apply_combi_route()
