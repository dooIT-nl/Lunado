import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # Standaard vult Odoo carrier_id nooit bij aanmaken: de voorkeur van de
    # klant (property_delivery_carrier_id) wordt alleen als default in de
    # wizard 'Verzendkosten toevoegen' gebruikt. Deze uitbreiding vult het
    # veld al bij het aanmaken van de offerte; precompute + store dekt zowel
    # de UI als API-creates.
    carrier_id = fields.Many2one(
        compute="_compute_carrier_id",
        store=True,
        readonly=False,
        precompute=True,
    )

    @api.depends("partner_shipping_id")
    def _compute_carrier_id(self):
        """Neem de standaard leveringswijze van het afleveradres over zodra
        dat wordt gezet of gewijzigd (terugval: commerciele partner —
        zelfde logica als de standaard verzendkosten-wizard). Alleen op
        openstaande offertes; een handmatige keuze of de waarde uit de
        verzendkosten-wizard blijft staan totdat het afleveradres opnieuw
        wijzigt, en wordt nooit leeggemaakt."""
        for order in self:
            carrier = order.carrier_id
            if not order.state or order.state in ("draft", "sent"):
                # property-veld is bedrijfsafhankelijk: lezen in het
                # bedrijf van de order
                partner = order.partner_shipping_id.with_company(
                    order.company_id
                )
                preferred = (
                    partner.property_delivery_carrier_id.filtered("active")
                    or partner.commercial_partner_id
                    .property_delivery_carrier_id.filtered("active")
                )
                if preferred:
                    carrier = preferred[:1]
            order.carrier_id = carrier
