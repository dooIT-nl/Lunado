import logging
from urllib.parse import urlencode

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_d1_open_framecalculator(self):
        """Open de externe framecalculator voor deze order.

        Bouwt de URL uit de instellingen (Verkoop > Instellingen >
        Framecalculator) met de order- en klant-id als parameters en opent
        die in het huidige venster — zelfde gedrag als de oude handmatige
        serveractie, maar zonder hardcoded URL/API-key.

        :return: ir.actions.act_url naar de framecalculator
        """
        self.ensure_one()
        # sudo: systeemparameters zijn niet leesbaar voor gewone gebruikers;
        # read-only configuratie voor het opbouwen van de URL.
        get_param = self.env["ir.config_parameter"].sudo().get_param
        base_url = (get_param("d1_framecalculator.url") or "").strip()
        api_key = (get_param("d1_framecalculator.api_key") or "").strip()
        if not base_url or not api_key:
            raise UserError(
                _(
                    "The frame calculator is not configured. Set the URL "
                    "and API key in Sales > Configuration > Settings, "
                    "section 'Framecalculator'."
                )
            )
        params = urlencode(
            {
                "apikey": api_key,
                "orderid": self.id,
                "customerid": self.partner_id.id,
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": "%s?%s" % (base_url.rstrip("/?"), params),
            "target": "self",
        }
