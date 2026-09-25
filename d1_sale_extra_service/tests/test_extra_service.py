from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "d1_sale_extra_service")
class TestD1SaleExtraService(TransactionCase):
    """Smoke tests voor de extra dienst per productcategorie (conversie C4)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "D1 Dienst klant"})
        cls.service = cls.env["product.product"].create(
            {"name": "D1 Zaagdienst", "type": "service", "list_price": 5.0}
        )
        cls.category = cls.env["product.category"].create(
            {
                "name": "D1 Zaaghout",
                "d1_extra_service_product_id": cls.service.product_tmpl_id.id,
            }
        )
        cls.product_a = cls.env["product.product"].create(
            {"name": "D1 Balk A", "categ_id": cls.category.id}
        )
        cls.product_b = cls.env["product.product"].create(
            {"name": "D1 Balk B", "categ_id": cls.category.id}
        )
        cls.product_plain = cls.env["product.product"].create(
            {"name": "D1 Gewoon product"}
        )

    def _create_order(self, lines, **vals):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (0, 0, {
                        "product_id": product.id,
                        "product_uom_qty": 1,
                        "d1_qty": qty,
                    })
                    for product, qty in lines
                ],
                **vals,
            }
        )

    def _service_line(self, order):
        return order.order_line.filtered(
            lambda l: l.product_id == self.service
        )

    def test_01_service_line_added(self):
        """Regel met categorie-dienst voegt de dienstregel toe met de som."""
        order = self._create_order([(self.product_a, 10.0)])
        service_line = self._service_line(order)
        self.assertEqual(len(service_line), 1)
        self.assertAlmostEqual(service_line.product_uom_qty, 10.0)

    def test_02_quantities_summed_over_lines(self):
        """Meerdere regels met dezelfde dienst worden gesommeerd."""
        order = self._create_order(
            [(self.product_a, 10.0), (self.product_b, 5.0)]
        )
        service_line = self._service_line(order)
        self.assertEqual(len(service_line), 1)
        self.assertAlmostEqual(service_line.product_uom_qty, 15.0)

    def test_03_qty_change_updates_service_line(self):
        """Wijzigen van de zaaghoeveelheid werkt de dienstregel bij."""
        order = self._create_order([(self.product_a, 10.0)])
        line = order.order_line.filtered(
            lambda l: l.product_id == self.product_a
        )
        line.write({"d1_qty": 25.0})
        self.assertAlmostEqual(
            self._service_line(order).product_uom_qty, 25.0
        )

    def test_04_no_service_without_category_link(self):
        """Producten zonder categorie-dienst voegen niets toe."""
        order = self._create_order([(self.product_plain, 10.0)])
        self.assertFalse(self._service_line(order))

    def test_05_orders_with_origin_skipped(self):
        """Orders met een bronndocument (origin) worden overgeslagen."""
        order = self._create_order(
            [(self.product_a, 10.0)], origin="SO-BRON"
        )
        self.assertFalse(self._service_line(order))
