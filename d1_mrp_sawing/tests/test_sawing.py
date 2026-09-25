from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "d1_mrp_sawing")
class TestD1MrpSawing(TransactionCase):
    """Smoke tests voor het zaag-cluster (Studio-conversie C6)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "D1 Zaag klant"})
        cls.saw_product = cls.env["product.product"].create(
            {
                "name": "D1 Zaagproduct",
                "is_storable": True,
                "weight": 2.5,
                "d1_use_qty": True,
                "d1_use_length": True,
                "d1_saw_capacity": 10,
                "d1_saw_time": 120,  # seconden per bewerking
            }
        )

    def _create_order_line(self, **line_vals):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    (0, 0, {
                        "product_id": self.saw_product.id,
                        "product_uom_qty": 1,
                        **line_vals,
                    })
                ],
            }
        )
        return order.order_line

    def test_01_use_length_requires_use_qty(self):
        """'Gebruik Lengte' zonder 'Gebruik Hoeveelheid' wordt geblokkeerd."""
        with self.assertRaises(ValidationError):
            self.env["product.product"].create(
                {
                    "name": "D1 Fout product",
                    "d1_use_length": True,
                    "d1_use_qty": False,
                }
            )

    def test_02_saw_values_required_for_manufacture_route(self):
        """Zaagcap/zaagtijd > 0 verplicht bij de productie-route."""
        route = self.env.ref("mrp.route_warehouse0_manufacture")
        with self.assertRaises(ValidationError):
            self.env["product.product"].create(
                {
                    "name": "D1 Productie zonder zaagcap",
                    "route_ids": [(4, route.id)],
                    "d1_saw_capacity": 0,
                    "d1_saw_time": 60,
                }
            )
        # met beide waarden > 0 mag het wel
        self.env["product.product"].create(
            {
                "name": "D1 Productie met zaagwaarden",
                "route_ids": [(4, route.id)],
                "d1_saw_capacity": 5,
                "d1_saw_time": 60,
            }
        )

    def test_03_qty_length_via_shipping_cost(self):
        """Orderhoeveelheid = hoeveelheid x lengte (logica uit
        d1_shipping_cost, integratietest)."""
        line = self._create_order_line(d1_qty=5.0, d1_length=2.4)
        self.assertAlmostEqual(line.product_uom_qty, 12.0)
        line.write({"d1_qty": 2.0, "d1_length": 3.0})
        self.assertAlmostEqual(line.product_uom_qty, 6.0)

    def test_04_use_flags_follow_template(self):
        """Gebruik-vlaggen op de regel volgen het product."""
        line = self._create_order_line(d1_qty=1.0, d1_length=1.0)
        self.assertTrue(line.d1_use_qty)
        self.assertTrue(line.d1_use_length)

    def test_05_weight_computed(self):
        """Gewicht = besteld aantal x productgewicht."""
        line = self._create_order_line(d1_qty=2.0, d1_length=2.0)
        # qty x lengte -> product_uom_qty = 4; gewicht = 4 x 2.5 = 10
        self.assertAlmostEqual(line.product_uom_qty, 4.0)
        self.assertAlmostEqual(line.d1_weight, 10.0)

    def test_06_frame_nr_computed(self):
        """Framenummer = ordernummer zonder 'S' + '-' + laatste 3 van ID."""
        line = self._create_order_line()
        line.order_id.name = "S00042"
        line.d1_frame_id = "FRAME-A17"
        self.assertEqual(line.d1_frame_nr, "00042-A17")
        line.d1_frame_id = False
        self.assertFalse(line.d1_frame_nr)

    def test_07_production_time_formula(self):
        """Productietijd = ceil(qty/zaagcap) x zaagtijd/60, hele minuten."""
        production = self.env["mrp.production"].create(
            {
                "product_id": self.saw_product.id,
                "product_qty": 1,
            }
        )
        production.d1_qty = 25  # 25/10 -> 3 bewerkingen x 120s/60 = 6 min
        self.assertEqual(production.d1_production_time, 6.0)
        production.d1_qty = 20  # exact deelbaar: 2 bewerkingen -> 4 min
        self.assertEqual(production.d1_production_time, 4.0)
        production.d1_qty = 0
        self.assertEqual(production.d1_production_time, 0.0)

    def test_08_workorder_duration_filled(self):
        """Werkorderduur (verwacht en werkelijk) = productietijd."""
        workcenter = self.env["mrp.workcenter"].create(
            {"name": "D1 Zaagbank"}
        )
        production = self.env["mrp.production"].create(
            {
                "product_id": self.saw_product.id,
                "product_qty": 1,
            }
        )
        production.d1_qty = 25  # -> 6 minuten
        workorder = self.env["mrp.workorder"].create(
            {
                "name": "D1 Zagen",
                "production_id": production.id,
                "workcenter_id": workcenter.id,
                "product_uom_id": self.saw_product.uom_id.id,
            }
        )
        self.assertEqual(workorder.duration_expected, 6.0)
        self.assertEqual(workorder.duration, 6.0)
