import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.onchange("partner_id")
    def _onchange_d1_partner_delivery_defaults(self):
        """Toon de leverdefaults van de leverancier direct in het formulier."""
        self._d1_apply_partner_delivery_defaults()

    @api.model_create_multi
    def create(self, vals_list):
        """Pas de leverdefaults van de leverancier toe bij aanmaken (dekt ook
        API-creates, net als de oorspronkelijke Studio-automation)."""
        orders = super().create(vals_list)
        orders._d1_apply_partner_delivery_defaults()
        return orders

    def write(self, vals):
        """Pas de leverdefaults opnieuw toe wanneer de leverancier wijzigt."""
        res = super().write(vals)
        if "partner_id" in vals:
            self._d1_apply_partner_delivery_defaults()
        return res

    def _d1_apply_partner_delivery_defaults(self):
        """Neem operatietype en incoterm van de leverancier over.

        Overslaan wanneer:
        * de leverancier geen leveroperatietype heeft ingesteld, of
        * het huidige operatietype van de order is uitgesloten via het vinkje
          'Geen leverdefaults van leverancier' (bv. Dropship).

        Conform de oorspronkelijke automation wordt de incoterm altijd mee
        overgenomen (ook als die bij de leverancier leeg is).
        """
        for order in self:
            partner = order.partner_id
            if not partner.d1_delivery_picking_type_id:
                continue
            if order.picking_type_id.d1_no_partner_delivery_default:
                continue
            if order.state not in ("draft", "sent"):
                continue
            order.picking_type_id = partner.d1_delivery_picking_type_id
            order.incoterm_id = partner.d1_incoterm_id
