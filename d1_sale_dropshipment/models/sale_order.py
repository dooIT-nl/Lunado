import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    d1_dropshipment = fields.Boolean(
        string="Dropshipment",
        compute="_compute_d1_dropshipment",
        store=True,
        readonly=False,
        precompute=True,
        help="Copied from the customer when the customer is set or changed; "
        "can be overridden per order.",
    )

    @api.depends("partner_id")
    def _compute_d1_dropshipment(self):
        """Neem de dropshipment-vlag van de klant over zodra de klant wordt
        gezet of gewijzigd. Werkt voor alle kanalen (UI-onchange en
        API-creates) en alle gebruikers; handmatig aanpassen per order blijft
        mogelijk totdat de klant opnieuw wijzigt."""
        for order in self:
            order.d1_dropshipment = order.partner_id.d1_dropshipment
