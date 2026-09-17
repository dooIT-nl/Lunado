import logging

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.model_create_multi
    def create(self, vals_list):
        """Pas de combi-routering toe op nieuwe regels van combi-orders."""
        lines = super().create(vals_list)
        lines._d1_apply_combi_route()
        return lines

    def write(self, vals):
        """Pas de combi-routering opnieuw toe wanneer het product wijzigt."""
        res = super().write(vals)
        if "product_id" in vals:
            self._d1_apply_combi_route()
        return res

    def _d1_apply_combi_route(self):
        """Zet de combi-route op regels van combi-orders.

        Regels (pariteit met de Studio-automations 'Combi order'):
        * Alleen voor combi-orders in offerte-status en regels met een
          fysiek product (goederen).
        * Een product zonder standaard magazijn blokkeert met een
          foutmelding.
        * Wijkt het standaard magazijn van het product af van het
          ordermagazijn, dan krijgt de regel de combi-route van het
          ordermagazijn; heeft dat magazijn geen combi-route, dan volgt een
          foutmelding ('combi nog niet actief').
        """
        for line in self:
            order = line.order_id
            if (
                not order.d1_combi
                or order.state not in ("draft", "sent")
                or line.display_type
                or line.product_id.type != "consu"
            ):
                continue
            default_wh = line.product_id.d1_default_warehouse_id
            if not default_wh:
                raise UserError(
                    _(
                        "The field Default Warehouse is not set for product "
                        "%s.",
                        line.product_id.display_name,
                    )
                )
            if default_wh == order.warehouse_id:
                continue
            combi_route = order.warehouse_id.d1_combi_route_id
            if not combi_route:
                raise UserError(
                    _(
                        "Combi orders for warehouse %s are not active yet: "
                        "no Combi Route is configured on the warehouse.",
                        order.warehouse_id.display_name,
                    )
                )
            # Odoo 19: route op de regel is een many2many (route_ids); de
            # combi-route vervangt eventuele eerdere routes op de regel.
            line.route_ids = combi_route
