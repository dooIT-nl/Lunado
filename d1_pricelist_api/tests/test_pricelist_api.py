from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "d1_pricelist_api")
class TestD1PricelistApi(TransactionCase):
    """Smoke tests for d1_api_get_customer_price (see CLAUDE.md section 12)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pricelist = cls.env["product.pricelist"].create({
            "name": "d1 Test Pricelist",
        })
        cls.partner = cls.env["res.partner"].create({
            "name": "d1 Test Customer",
            "property_product_pricelist": cls.pricelist.id,
        })
        cls.product = cls.env["product.product"].create({
            "name": "d1 Test Product",
            "list_price": 100.0,
        })
        # Tier rule: 10% discount from 10 pieces.
        cls.env["product.pricelist.item"].create({
            "pricelist_id": cls.pricelist.id,
            "applied_on": "1_product",
            "product_tmpl_id": cls.product.product_tmpl_id.id,
            "min_quantity": 10,
            "compute_price": "percentage",
            "percent_price": 10.0,
        })

    def test_price_single_quantity(self):
        """Quantity 1 falls outside the tier rule: list price applies."""
        result = self.env["product.pricelist"].d1_api_get_customer_price(
            self.partner.id, self.product.id, 1.0
        )
        self.assertEqual(result["price"], 100.0)
        self.assertEqual(result["pricelist_id"], self.pricelist.id)
        self.assertEqual(result["partner_id"], self.partner.id)
        self.assertEqual(result["product_id"], self.product.id)

    def test_price_tier_quantity(self):
        """Quantity 10 triggers the 10% tier rule."""
        result = self.env["product.pricelist"].d1_api_get_customer_price(
            self.partner.id, self.product.id, 10.0
        )
        self.assertEqual(result["price"], 90.0)

    def test_unknown_partner_raises(self):
        with self.assertRaises(UserError):
            self.env["product.pricelist"].d1_api_get_customer_price(
                99999999, self.product.id, 1.0
            )

    def test_unknown_product_raises(self):
        with self.assertRaises(UserError):
            self.env["product.pricelist"].d1_api_get_customer_price(
                self.partner.id, 99999999, 1.0
            )

    def test_invalid_quantity_raises(self):
        with self.assertRaises(UserError):
            self.env["product.pricelist"].d1_api_get_customer_price(
                self.partner.id, self.product.id, 0.0
            )
