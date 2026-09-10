from datetime import timedelta

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "d1_sale_commitment_date")
class TestD1CommitmentDate(TransactionCase):
    """Smoke tests voor de berekening van de leverdatum uit orderregels."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.partner = cls.env["res.partner"].create({"name": "D1 Test Klant"})
        cls.product_stock = cls.env["product.product"].create(
            {
                "name": "D1 Product op voorraad",
                "is_storable": True,
                "sale_delay": 10,
            }
        )
        cls.product_no_stock = cls.env["product.product"].create(
            {
                "name": "D1 Product zonder voorraad",
                "is_storable": True,
                "sale_delay": 7,
            }
        )
        cls.env["stock.quant"]._update_available_quantity(
            cls.product_stock, cls.warehouse.lot_stock_id, 100
        )

    def _create_order(self, lines):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.warehouse.id,
                "order_line": [
                    (0, 0, {"product_id": product.id, "product_uom_qty": qty})
                    for product, qty in lines
                ],
            }
        )

    def test_01_sufficient_stock_no_sale_delay(self):
        """Voldoende voorraad -> leverdatum vandaag, sale_delay genegeerd."""
        order = self._create_order([(self.product_stock, 5)])
        self.assertTrue(order.commitment_date)
        self.assertLess(
            order.commitment_date,
            fields.Datetime.now() + timedelta(days=1),
            "Met voldoende voorraad mag de sale_delay niet meetellen",
        )

    def test_02_no_stock_no_picking_uses_sale_delay(self):
        """Geen voorraad en geen ontvangst -> nu + sale_delay."""
        order = self._create_order([(self.product_no_stock, 5)])
        expected = fields.Datetime.now() + timedelta(days=7)
        self.assertTrue(order.commitment_date)
        self.assertAlmostEqual(
            order.commitment_date,
            expected,
            delta=timedelta(minutes=5),
        )

    def test_03_no_stock_with_incoming_picking(self):
        """Geen voorraad, wel geplande ontvangst -> scheduled_date picking."""
        scheduled = fields.Datetime.now() + timedelta(days=30)
        picking_type = self.warehouse.in_type_id
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": self.env.ref("stock.stock_location_suppliers").id,
                "location_dest_id": self.warehouse.lot_stock_id.id,
                "scheduled_date": scheduled,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_no_stock.id,
                            "product_uom_qty": 50,
                            "location_id": self.env.ref(
                                "stock.stock_location_suppliers"
                            ).id,
                            "location_dest_id": self.warehouse.lot_stock_id.id,
                        },
                    )
                ],
            }
        )
        picking.action_confirm()
        order = self._create_order([(self.product_no_stock, 5)])
        self.assertAlmostEqual(
            order.commitment_date,
            scheduled,
            delta=timedelta(minutes=5),
        )

    def test_04_order_takes_latest_line_date(self):
        """Laatste regeldatum bepaalt de leverdatum van de order."""
        order = self._create_order(
            [(self.product_stock, 5), (self.product_no_stock, 5)]
        )
        expected = fields.Datetime.now() + timedelta(days=7)
        self.assertAlmostEqual(
            order.commitment_date,
            expected,
            delta=timedelta(minutes=5),
        )

    def test_05_kit_bom_explodes_components(self):
        """Kit -> componenten bepalen de datum (aantal x stuklijstregel)."""
        kit = self.env["product.product"].create(
            {"name": "D1 Kit", "is_storable": True, "sale_delay": 0}
        )
        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": kit.product_tmpl_id.id,
                "type": "phantom",
                "product_qty": 1,
                "bom_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_no_stock.id,
                            "product_qty": 2,
                        },
                    )
                ],
            }
        )
        order = self._create_order([(kit, 3)])
        expected = fields.Datetime.now() + timedelta(days=7)
        self.assertAlmostEqual(
            order.commitment_date,
            expected,
            delta=timedelta(minutes=5),
            msg="Kitcomponent zonder voorraad moet sale_delay component volgen",
        )

    def test_06_customer_request_date(self):
        """Latere klantdatum wint; eerdere klantdatum geeft waarschuwing."""
        order = self._create_order([(self.product_no_stock, 5)])
        later = fields.Datetime.now() + timedelta(days=60)
        order.d1_customer_request_date = later
        self.assertEqual(order.commitment_date, later)
        self.assertFalse(order.d1_delivery_date_warning)
        earlier = fields.Datetime.now() + timedelta(days=1)
        order.d1_customer_request_date = earlier
        self.assertTrue(order.d1_delivery_date_warning)
        self.assertNotEqual(order.commitment_date, earlier)
