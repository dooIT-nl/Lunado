import logging

from odoo import api, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class D1ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    @api.model
    def d1_api_get_customer_price(self, partner_id, product_id, quantity=1.0):
        """Publieke API-methode voor de Odoo 19 JSON-2 API.

        Berekent de netto verkoopprijs (excl. btw) van een product voor een
        specifieke klant, volgens de prijslijst die aan die klant is gekoppeld
        (veld ``property_product_pricelist`` op res.partner). Staffelprijzen
        worden meegenomen via de ``quantity``-parameter.

        Aanroep (extern):
            POST {host}/json/2/product.pricelist/d1_api_get_customer_price
            {"partner_id": 42, "product_id": 3, "quantity": 10.0}

        :param int partner_id: ID van de klant (res.partner)
        :param int product_id: ID van het product (product.product)
        :param float quantity: aantal, voor staffelprijzen (default 1.0)
        :returns: dict met de berekende prijs en context-informatie
        :rtype: dict
        :raises UserError: bij onbekende klant/product of ongeldige quantity
        """
        partner = self.env["res.partner"].browse(int(partner_id))
        if not partner.exists():
            raise UserError(
                _("Customer with ID %s does not exist.", partner_id)
            )

        product = self.env["product.product"].browse(int(product_id))
        if not product.exists():
            raise UserError(
                _("Product with ID %s does not exist.", product_id)
            )

        quantity = float(quantity)
        if quantity <= 0:
            raise UserError(_("Quantity must be greater than 0."))

        pricelist = partner.property_product_pricelist
        if not pricelist:
            raise UserError(
                _("No pricelist found for customer with ID %s.", partner_id)
            )

        # Same internal computation used by sale orders and the webshop.
        # Returned price is excl. VAT.
        price = pricelist._get_product_price(product, quantity)

        _logger.info(
            "d1_api_get_customer_price: partner=%s product=%s qty=%s "
            "pricelist=%s price=%s",
            partner.id, product.id, quantity, pricelist.id, price,
        )

        return {
            "partner_id": partner.id,
            "partner_name": partner.display_name,
            "product_id": product.id,
            "product_name": product.display_name,
            "quantity": quantity,
            "price": price,
            "price_note": "excl. VAT",
            "pricelist_id": pricelist.id,
            "pricelist_name": pricelist.display_name,
            "currency": pricelist.currency_id.name,
        }
