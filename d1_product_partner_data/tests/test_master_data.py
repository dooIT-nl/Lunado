from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "d1_product_partner_data")
class TestD1ProductPartnerData(TransactionCase):
    """Smoke tests voor de stamdatavelden (Studio-conversie C7)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "D1 Stamdata product",
                "is_storable": True,
                "d1_abc_code": "05",
                "d1_courant": True,
                "d1_cost_calc": 12.34,
            }
        )

    def test_01_master_data_fields(self):
        """Smoke: stamdatavelden zijn instelbaar."""
        self.assertEqual(self.product.d1_abc_code, "05")
        self.assertTrue(self.product.d1_courant)
        self.assertAlmostEqual(self.product.d1_cost_calc, 12.34)

    def test_02_available_follows_stock(self):
        """Beschikbaar = voorraad > 0 (bug uit Studio-versie gefixt)."""
        template = self.product.product_tmpl_id
        self.assertFalse(template.d1_available)
        self.env["stock.quant"]._update_available_quantity(
            self.product, self.warehouse.lot_stock_id, 10
        )
        template.invalidate_recordset()
        template._compute_d1_available()
        self.assertTrue(template.d1_available)

    def test_03_available_false_for_subcontract_bom(self):
        """Product met subcontract-stuklijst is nooit beschikbaar."""
        bom_type_field = self.env["mrp.bom"]._fields["type"]
        selection_values = [
            value for value, _label in bom_type_field.selection
        ]
        if "subcontract" not in selection_values:
            self.skipTest("mrp_subcontracting niet geinstalleerd")
        product = self.env["product.product"].create(
            {"name": "D1 Uitbesteed product", "is_storable": True}
        )
        self.env["stock.quant"]._update_available_quantity(
            product, self.warehouse.lot_stock_id, 10
        )
        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": product.product_tmpl_id.id,
                "type": "subcontract",
                "product_qty": 1,
            }
        )
        self.assertFalse(product.product_tmpl_id.d1_available)

    def test_04_package_count(self):
        """Aantal verpakkingen = aantal verpakkings-UoM's."""
        template = self.product.product_tmpl_id
        self.assertEqual(template.d1_package_count, len(template.uom_ids))

    def test_05_delivery_note_url(self):
        """Smoke: pakbon-URL is instelbaar op de order."""
        partner = self.env["res.partner"].create({"name": "D1 URL klant"})
        order = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "d1_delivery_note_url": "https://example.com/pakbon/1",
            }
        )
        self.assertTrue(order.d1_delivery_note_url.startswith("https://"))
