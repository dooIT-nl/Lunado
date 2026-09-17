from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "d1_sale_combi")
class TestD1SaleCombi(TransactionCase):
    """Smoke tests voor combi-orders (Studio-conversie C5)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.wh_main = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.wh_other = cls.env["stock.warehouse"].create(
            {"name": "D1 Magazijn 2", "code": "D1WH2"}
        )
        cls.combi_route = cls.env["stock.route"].create(
            {
                "name": "D1 Combi hoofdmagazijn: Lever in 3 stappen",
                "sale_selectable": True,
                "warehouse_selectable": True,
                "warehouse_ids": [(4, cls.wh_main.id)],
            }
        )
        cls.wh_main.d1_combi_route_id = cls.combi_route
        cls.partner = cls.env["res.partner"].create({"name": "D1 Combi klant"})
        cls.product_local = cls.env["product.product"].create(
            {
                "name": "D1 Product hoofdmagazijn",
                "is_storable": True,
                "d1_default_warehouse_id": cls.wh_main.id,
            }
        )
        cls.product_remote = cls.env["product.product"].create(
            {
                "name": "D1 Product ander magazijn",
                "is_storable": True,
                "d1_default_warehouse_id": cls.wh_other.id,
            }
        )
        cls.product_no_wh = cls.env["product.product"].create(
            {"name": "D1 Product zonder magazijn", "is_storable": True}
        )
        cls.service = cls.env["product.product"].create(
            {"name": "D1 Dienst", "type": "service"}
        )

    def _create_order(self, products, combi=True):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.wh_main.id,
                "d1_combi": combi,
                "order_line": [
                    (0, 0, {"product_id": p.id, "product_uom_qty": 1})
                    for p in products
                ],
            }
        )

    def test_01_remote_product_gets_combi_route(self):
        """Product met afwijkend magazijn krijgt de combi-route."""
        order = self._create_order([self.product_local, self.product_remote])
        local_line = order.order_line.filtered(
            lambda l: l.product_id == self.product_local
        )
        remote_line = order.order_line.filtered(
            lambda l: l.product_id == self.product_remote
        )
        self.assertFalse(local_line.route_ids)
        self.assertEqual(remote_line.route_ids, self.combi_route)

    def test_02_non_combi_order_untouched(self):
        """Zonder combi-vlag gebeurt er niets."""
        order = self._create_order([self.product_remote], combi=False)
        self.assertFalse(order.order_line.route_ids)

    def test_03_missing_default_warehouse_blocks(self):
        """Product zonder standaard magazijn blokkeert combi-orders."""
        with self.assertRaises(UserError):
            self._create_order([self.product_no_wh])

    def test_04_service_lines_ignored(self):
        """Diensten worden overgeslagen (geen magazijn nodig)."""
        order = self._create_order([self.service])
        self.assertFalse(order.order_line.route_ids)

    def test_05_no_combi_route_blocks(self):
        """Magazijn zonder combi-route blokkeert ('nog niet actief')."""
        self.wh_main.d1_combi_route_id = False
        with self.assertRaises(UserError):
            self._create_order([self.product_remote])

    def test_06_flag_set_later_applies_routes(self):
        """Combi-vlag achteraf aanzetten routeert bestaande regels alsnog."""
        order = self._create_order([self.product_remote], combi=False)
        self.assertFalse(order.order_line.route_ids)
        order.d1_combi = True
        self.assertEqual(order.order_line.route_ids, self.combi_route)
