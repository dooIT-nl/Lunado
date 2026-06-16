import logging
import math

from odoo.tests.common import TransactionCase, tagged

_logger = logging.getLogger(__name__)


@tagged("d1_shipping_cost", "-at_install", "post_install")
class TestTransportCost(TransactionCase):
    """Unit tests for the d1_shipping_cost transport cost calculation module.

    Tests cover TK1 (bundle), TK2 (box/weight), and TK3 (display) flows,
    including edge cases for rounding (floor/ceil), weight corrections,
    and pallet/exception flags.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.country_nl = cls.env.ref("base.nl")

        # Shipping classes — codes are uppercase in the database
        ShippingClass = cls.env["d1.shipping.class"]
        cls.class_tk1 = ShippingClass.search([("code", "=ilike", "TK1")], limit=1)
        cls.class_tk2 = ShippingClass.search([("code", "=ilike", "TK2")], limit=1)
        cls.class_tk3 = ShippingClass.search([("code", "=ilike", "TK3")], limit=1)
        if not cls.class_tk1:
            cls.class_tk1 = ShippingClass.create({"name": "TK1", "code": "TK1"})
        if not cls.class_tk2:
            cls.class_tk2 = ShippingClass.create({"name": "TK2", "code": "TK2"})
        if not cls.class_tk3:
            cls.class_tk3 = ShippingClass.create({"name": "TK3", "code": "TK3"})

        # Set config parameters
        ICP = cls.env["ir.config_parameter"].sudo()
        ICP.set_param("d1_shipping.bundle_width_cm", "15")
        ICP.set_param("d1_shipping.bundle_height_cm", "15")
        ICP.set_param("d1_shipping.bundle_max_weight_kg", "20")
        ICP.set_param("d1_shipping.box_max_weight_kg", "20")
        ICP.set_param("d1_shipping.tk1_max_bundels", "20")
        ICP.set_param("d1_shipping.tk2_max_gewicht_kg", "200")
        ICP.set_param("d1_shipping.tk3_max_gewicht_kg", "200")

        # Partner with NL address
        cls.partner = cls.env["res.partner"].create({
            "name": "Test Partner",
            "country_id": cls.country_nl.id,
        })

        # ---- Products ----
        cls.product_tk1 = cls.env["product.product"].create({
            "name": "Test Tube TK1",
            "type": "consu",
            "d1_shipping_class_id": cls.class_tk1.id,
            "d1_length_cm": 150.0,
            "d1_width_cm": 3.0,
            "d1_height_cm": 3.0,
            "weight": 2.0,
            "list_price": 10.0,
        })
        cls.product_tk1_long = cls.env["product.product"].create({
            "name": "Test Long Tube TK1",
            "type": "consu",
            "d1_shipping_class_id": cls.class_tk1.id,
            "d1_length_cm": 220.0,
            "d1_width_cm": 5.0,
            "d1_height_cm": 5.0,
            "weight": 5.0,
            "list_price": 20.0,
        })
        cls.product_tk2 = cls.env["product.product"].create({
            "name": "Test Coupling TK2",
            "type": "consu",
            "d1_shipping_class_id": cls.class_tk2.id,
            "d1_length_cm": 10.0,
            "d1_width_cm": 5.0,
            "d1_height_cm": 5.0,
            "weight": 0.5,
            "list_price": 5.0,
        })
        cls.product_tk3_small = cls.env["product.product"].create({
            "name": "Test Display TK3 Small",
            "type": "consu",
            "d1_shipping_class_id": cls.class_tk3.id,
            "d1_length_cm": 60.0,
            "d1_width_cm": 40.0,
            "d1_height_cm": 30.0,
            "weight": 2.0,
            "list_price": 50.0,
        })
        cls.product_tk3_heavy = cls.env["product.product"].create({
            "name": "Test Display TK3 Heavy",
            "type": "consu",
            "d1_shipping_class_id": cls.class_tk3.id,
            "d1_length_cm": 80.0,
            "d1_width_cm": 60.0,
            "d1_height_cm": 50.0,
            "weight": 25.0,
            "list_price": 100.0,
        })
        cls.product_tk3_oversized = cls.env["product.product"].create({
            "name": "Test Display TK3 Oversized",
            "type": "consu",
            "d1_shipping_class_id": cls.class_tk3.id,
            "d1_length_cm": 170.0,
            "d1_width_cm": 40.0,
            "d1_height_cm": 30.0,
            "weight": 10.0,
            "list_price": 200.0,
        })
        cls.product_tk3_girth = cls.env["product.product"].create({
            "name": "Test Display TK3 Girth",
            "type": "consu",
            "d1_shipping_class_id": cls.class_tk3.id,
            "d1_length_cm": 100.0,
            "d1_width_cm": 60.0,
            "d1_height_cm": 50.0,
            "weight": 10.0,
            "list_price": 150.0,
        })
        cls.product_no_class = cls.env["product.product"].create({
            "name": "Test No Class",
            "type": "consu",
            "list_price": 30.0,
        })

        # ---- Length brackets ----
        LB = cls.env["d1.shipping.length.bracket"]
        cls.bracket_lt_165 = LB.search([("length_from_cm", "=", 0), ("length_to_cm", "=", 164)], limit=1)
        cls.bracket_gte_215 = LB.search([("length_from_cm", "=", 215), ("length_to_cm", "=", 0)], limit=1)
        if not cls.bracket_lt_165:
            cls.bracket_lt_165 = LB.create({"name": "< 1,65 m", "length_from_cm": 0, "length_to_cm": 164})
        if not cls.bracket_gte_215:
            cls.bracket_gte_215 = LB.create({"name": ">= 2,15 m", "length_from_cm": 215, "length_to_cm": 0})

        # ---- Transport rates (NL) ----
        Rate = cls.env["d1.shipping.rate"]
        Rate.create({
            "name": "TK1 NL <1.65m 1-10",
            "shipping_class_id": cls.class_tk1.id,
            "country_ids": [(6, 0, [cls.country_nl.id])],
            "length_bracket_id": cls.bracket_lt_165.id,
            "unit_type": "bundle",
            "qty_from": 1, "qty_to": 10,
            "price": 25.0,
        })
        Rate.create({
            "name": "TK1 NL <1.65m 11-19",
            "shipping_class_id": cls.class_tk1.id,
            "country_ids": [(6, 0, [cls.country_nl.id])],
            "length_bracket_id": cls.bracket_lt_165.id,
            "unit_type": "bundle",
            "qty_from": 11, "qty_to": 19,
            "price": 45.0,
        })
        Rate.create({
            "name": "TK1 NL >=2.15m 1-10",
            "shipping_class_id": cls.class_tk1.id,
            "country_ids": [(6, 0, [cls.country_nl.id])],
            "length_bracket_id": cls.bracket_gte_215.id,
            "unit_type": "bundle",
            "qty_from": 1, "qty_to": 10,
            "price": 50.0,
        })
        Rate.create({
            "name": "TK2 NL 1-5 boxes",
            "shipping_class_id": cls.class_tk2.id,
            "country_ids": [(6, 0, [cls.country_nl.id])],
            "unit_type": "box",
            "qty_from": 1, "qty_to": 5,
            "price": 15.0,
        })
        Rate.create({
            "name": "TK2 NL 6-10 boxes",
            "shipping_class_id": cls.class_tk2.id,
            "country_ids": [(6, 0, [cls.country_nl.id])],
            "unit_type": "box",
            "qty_from": 6, "qty_to": 10,
            "price": 28.0,
        })
        Rate.create({
            "name": "TK3 NL 1-5 boxes",
            "shipping_class_id": cls.class_tk3.id,
            "country_ids": [(6, 0, [cls.country_nl.id])],
            "unit_type": "box",
            "qty_from": 1, "qty_to": 5,
            "price": 20.0,
        })

    def _create_order(self, lines_data):
        """Helper: create a sale.order with given lines.

        lines_data: list of (product, qty) tuples.
        """
        order = self.env["sale.order"].create({
            "partner_id": self.partner.id,
        })
        for product, qty in lines_data:
            self.env["sale.order.line"].create({
                "order_id": order.id,
                "product_id": product.id,
                "product_uom_qty": qty,
            })
        return order

    # ------------------------------------------------------------------
    # TK1 Tests
    # ------------------------------------------------------------------

    def test_tk1_bundle_calculation_basic(self):
        """TK1: basic bundle count with floor rounding for tubes per bundle."""
        order = self._create_order([(self.product_tk1, 50)])
        order.action_d1_compute_transport_cost()

        self.assertIn("TK1", order.d1_transport_message)
        transport_product = self.env.ref("d1_shipping_cost.product_transport_cost")
        transport_line = order.order_line.filtered(lambda l: l.product_id == transport_product)
        self.assertTrue(transport_line, "Transport cost line should exist")
        self.assertEqual(transport_line.price_unit, 25.0)

    def test_tk1_long_tube_bracket(self):
        """TK1: long tube (220cm >= 215cm) uses gte_215 bracket."""
        order = self._create_order([(self.product_tk1_long, 9)])
        order.action_d1_compute_transport_cost()

        transport_product = self.env.ref("d1_shipping_cost.product_transport_cost")
        transport_line = order.order_line.filtered(lambda l: l.product_id == transport_product)
        self.assertTrue(transport_line)
        self.assertEqual(transport_line.price_unit, 50.0)

    def test_tk1_pallet_threshold(self):
        """TK1: bundles >= max → pallet flag (manual)."""
        order = self._create_order([(self.product_tk1, 500)])
        order.action_d1_compute_transport_cost()

        self.assertIn("PALLETBEREKENING", order.d1_transport_message)
        transport_product = self.env.ref("d1_shipping_cost.product_transport_cost")
        transport_line = order.order_line.filtered(lambda l: l.product_id == transport_product)
        self.assertFalse(transport_line, "No transport line when pallet required")

    # ------------------------------------------------------------------
    # TK2 Tests
    # ------------------------------------------------------------------

    def test_tk2_box_calculation(self):
        """TK2: basic box count by weight."""
        order = self._create_order([(self.product_tk2, 30)])
        order.action_d1_compute_transport_cost()

        transport_product = self.env.ref("d1_shipping_cost.product_transport_cost")
        transport_line = order.order_line.filtered(lambda l: l.product_id == transport_product)
        self.assertTrue(transport_line)
        self.assertEqual(transport_line.price_unit, 15.0)

    def test_tk2_multiple_boxes(self):
        """TK2: multiple boxes from weight calculation."""
        # 200 couplings * 0.5kg = 100kg → ceil(100/20) = 5 boxes
        # Rate lookup: 5 boxes matches 1-5 and 4-10 staffels;
        # search picks highest qty_from → 4-10 (price 25.0)
        order = self._create_order([(self.product_tk2, 200)])
        order.action_d1_compute_transport_cost()

        transport_product = self.env.ref("d1_shipping_cost.product_transport_cost")
        transport_line = order.order_line.filtered(lambda l: l.product_id == transport_product)
        self.assertTrue(transport_line)
        self.assertEqual(transport_line.price_unit, 25.0)

    def test_tk2_pallet_threshold(self):
        """TK2: weight >= threshold → pallet flag."""
        order = self._create_order([(self.product_tk2, 800)])
        order.action_d1_compute_transport_cost()

        self.assertIn("PALLETBEREKENING", order.d1_transport_message)

    # ------------------------------------------------------------------
    # TK3 Tests
    # ------------------------------------------------------------------

    def test_tk3_box_calculation(self):
        """TK3: small display within all limits → box calculation."""
        order = self._create_order([(self.product_tk3_small, 5)])
        order.action_d1_compute_transport_cost()

        transport_product = self.env.ref("d1_shipping_cost.product_transport_cost")
        transport_line = order.order_line.filtered(lambda l: l.product_id == transport_product)
        self.assertTrue(transport_line)
        self.assertEqual(transport_line.price_unit, 20.0)

    def test_tk3_heavy_article_pallet(self):
        """TK3: single article >= 20kg → pallet flag."""
        order = self._create_order([(self.product_tk3_heavy, 1)])
        order.action_d1_compute_transport_cost()

        self.assertIn("PALLETBEREKENING", order.d1_transport_message)

    def test_tk3_oversized_exception(self):
        """TK3: dimension >= 165cm → Wesseling/Mainfreight exception."""
        order = self._create_order([(self.product_tk3_oversized, 1)])
        order.action_d1_compute_transport_cost()

        self.assertIn("UITZONDERING", order.d1_transport_message)
        self.assertIn("Wesseling", order.d1_transport_message)

    def test_tk3_girth_exception(self):
        """TK3: L+2W+2H >= 300cm → Wesseling/Mainfreight exception."""
        order = self._create_order([(self.product_tk3_girth, 1)])
        order.action_d1_compute_transport_cost()

        self.assertIn("UITZONDERING", order.d1_transport_message)

    def test_tk3_pallet_threshold(self):
        """TK3: total weight >= threshold → pallet flag."""
        order = self._create_order([(self.product_tk3_small, 100)])
        order.action_d1_compute_transport_cost()

        self.assertIn("PALLETBEREKENING", order.d1_transport_message)

    # ------------------------------------------------------------------
    # Mixed / Edge case tests
    # ------------------------------------------------------------------

    def test_no_transport_class_ignored(self):
        """Products without transport class are ignored."""
        order = self._create_order([(self.product_no_class, 10)])
        order.action_d1_compute_transport_cost()

        self.assertIn("overgeslagen", order.d1_transport_message)
        transport_product = self.env.ref("d1_shipping_cost.product_transport_cost")
        transport_line = order.order_line.filtered(lambda l: l.product_id == transport_product)
        self.assertFalse(transport_line)

    def test_mixed_classes(self):
        """Mixed order with TK1 and TK2 products."""
        order = self._create_order([
            (self.product_tk1, 10),
            (self.product_tk2, 30),
        ])
        order.action_d1_compute_transport_cost()

        transport_product = self.env.ref("d1_shipping_cost.product_transport_cost")
        transport_line = order.order_line.filtered(lambda l: l.product_id == transport_product)
        self.assertTrue(transport_line)
        self.assertEqual(transport_line.price_unit, 40.0)

    def test_recalculation_replaces_line(self):
        """Re-running the calculation replaces the existing transport line."""
        order = self._create_order([(self.product_tk2, 30)])
        order.action_d1_compute_transport_cost()

        transport_product = self.env.ref("d1_shipping_cost.product_transport_cost")
        lines_before = order.order_line.filtered(lambda l: l.product_id == transport_product)
        self.assertEqual(len(lines_before), 1)

        order.action_d1_compute_transport_cost()
        lines_after = order.order_line.filtered(lambda l: l.product_id == transport_product)
        self.assertEqual(len(lines_after), 1, "Should still be exactly one transport line")
