from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "d1_studio_compat")
class TestD1StudioCompat(TransactionCase):
    """Smoke tests: oude x_studio-veldnamen werken via de aliassen (API)."""

    def test_01_product_alias_read_write(self):
        """Product-aliassen lezen en schrijven door naar de d1_-velden."""
        product = self.env["product.product"].create(
            {"name": "Compat product", "x_studio_zaagcap_bew": 12}
        )
        self.assertEqual(product.d1_saw_capacity, 12)
        product.product_tmpl_id.d1_abc_code = "05"
        self.assertEqual(product.x_studio_abc_code, "05")
        # search_read via het oude veld (het API-pad dat stukliep)
        rows = self.env["product.product"].search_read(
            [("id", "=", product.id)],
            ["name", "x_studio_artikelcode_gezaagd", "x_studio_zaagcap_bew"],
        )
        self.assertEqual(rows[0]["x_studio_zaagcap_bew"], 12)

    def test_02_partner_value_mapping(self):
        """Oude Studio-waarden (Prospect/Klant, verzekeringslabels) blijven
        geldig via de vertaalde aliassen."""
        partner = self.env["res.partner"].create(
            {
                "name": "Compat klant",
                "x_studio_rel_type": "Klant",
                "x_studio_kredietverzekering": "Niet verzekerd",
            }
        )
        self.assertEqual(partner.d1_rel_type, "customer")
        self.assertEqual(partner.d1_credit_insurance, "not_insured")
        partner.d1_rel_type = "prospect"
        self.assertEqual(partner.x_studio_rel_type, "Prospect")

    def test_03_order_line_alias(self):
        """Orderregel-aliassen (het API-orderpad) werken door."""
        partner = self.env["res.partner"].create({"name": "Compat order"})
        product = self.env["product.product"].create(
            {"name": "Compat lijn", "d1_use_qty": True, "d1_use_length": True}
        )
        order = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "x_studio_dropshipment": True,
                "order_line": [
                    (0, 0, {
                        "product_id": product.id,
                        "x_studio_qty": 5.0,
                        "x_studio_length": 2.0,
                    })
                ],
            }
        )
        self.assertTrue(order.d1_dropshipment)
        line = order.order_line
        self.assertEqual(line.d1_qty, 5.0)
        # qty x lengte-logica (d1_shipping_cost) draait op de nieuwe velden
        self.assertAlmostEqual(line.product_uom_qty, 10.0)
