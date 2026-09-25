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

        # -- Weight banding products --
        # TK1 mid-band: weight 15 kg (>= 20/2=10, < 20) → one per bundle
        cls.product_tk1_mid = cls.env["product.product"].create({
            "name": "Test Tube TK1 Mid-weight",
            "type": "consu",
            "d1_shipping_class_id": cls.class_tk1.id,
            "d1_length_cm": 150.0,
            "d1_width_cm": 3.0,
            "d1_height_cm": 3.0,
            "weight": 15.0,
            "list_price": 10.0,
        })
        # TK1 heavy: weight 25 kg (>= 20) → pallet
        cls.product_tk1_heavy = cls.env["product.product"].create({
            "name": "Test Tube TK1 Heavy",
            "type": "consu",
            "d1_shipping_class_id": cls.class_tk1.id,
            "d1_length_cm": 150.0,
            "d1_width_cm": 5.0,
            "d1_height_cm": 5.0,
            "weight": 25.0,
            "list_price": 20.0,
        })
        # TK2 mid-band: weight 12 kg (>= 20/2=10, < 20) → one per box
        cls.product_tk2_mid = cls.env["product.product"].create({
            "name": "Test Coupling TK2 Mid-weight",
            "type": "consu",
            "d1_shipping_class_id": cls.class_tk2.id,
            "d1_length_cm": 10.0,
            "d1_width_cm": 5.0,
            "d1_height_cm": 5.0,
            "weight": 12.0,
            "list_price": 15.0,
        })
        # TK2 heavy: weight 22 kg (>= 20) → pallet
        cls.product_tk2_heavy = cls.env["product.product"].create({
            "name": "Test Coupling TK2 Heavy",
            "type": "consu",
            "d1_shipping_class_id": cls.class_tk2.id,
            "d1_length_cm": 10.0,
            "d1_width_cm": 5.0,
            "d1_height_cm": 5.0,
            "weight": 22.0,
            "list_price": 25.0,
        })

        # ---- Length brackets ----
        LB = cls.env["d1.shipping.length.bracket"]
        cls.bracket_lt_165 = LB.search([("length_from_cm", "=", 0), ("length_to_cm", "=", 164)], limit=1)
        cls.bracket_gte_215 = LB.search([("length_from_cm", "=", 215), ("length_to_cm", "=", 0)], limit=1)
        if not cls.bracket_lt_165:
            cls.bracket_lt_165 = LB.create({"name": "< 1,65 m", "length_from_cm": 0, "length_to_cm": 164})
        if not cls.bracket_gte_215:
            cls.bracket_gte_215 = LB.create({"name": ">= 2,15 m", "length_from_cm": 215, "length_to_cm": 0})

        # ---- Carriers (transporteurs via delivery.carrier) ----
        Carrier = cls.env["delivery.carrier"]
        carrier_product = cls.env["product.product"].create({
            "name": "Carrier Service",
            "type": "service",
            "list_price": 0.0,
        })
        cls.carrier_tk1 = Carrier.create({
            "name": "Transporteur TK1",
            "delivery_type": "fixed",
            "product_id": carrier_product.id,
        })
        cls.carrier_tk2 = Carrier.create({
            "name": "Transporteur TK2",
            "delivery_type": "fixed",
            "product_id": carrier_product.id,
        })
        cls.carrier_tk3 = Carrier.create({
            "name": "Transporteur TK3",
            "delivery_type": "fixed",
            "product_id": carrier_product.id,
        })

        # Remove any pre-existing rates to avoid conflicts with test data
        Rate = cls.env["d1.shipping.rate"]
        Rate.search([]).unlink()
        Rate.create({
            "name": "TK1 NL <1.65m 1-10",
            "shipping_class_id": cls.class_tk1.id,
            "country_ids": [(6, 0, [cls.country_nl.id])],
            "length_bracket_id": cls.bracket_lt_165.id,
            "unit_type": "bundle",
            "qty_from": 1, "qty_to": 10,
            "price": 25.0,
            "carrier_id": cls.carrier_tk1.id,
        })
        Rate.create({
            "name": "TK1 NL <1.65m 11-19",
            "shipping_class_id": cls.class_tk1.id,
            "country_ids": [(6, 0, [cls.country_nl.id])],
            "length_bracket_id": cls.bracket_lt_165.id,
            "unit_type": "bundle",
            "qty_from": 11, "qty_to": 19,
            "price": 45.0,
            "carrier_id": cls.carrier_tk1.id,
        })
        Rate.create({
            "name": "TK1 NL >=2.15m 1-10",
            "shipping_class_id": cls.class_tk1.id,
            "country_ids": [(6, 0, [cls.country_nl.id])],
            "length_bracket_id": cls.bracket_gte_215.id,
            "unit_type": "bundle",
            "qty_from": 1, "qty_to": 10,
            "price": 50.0,
            "carrier_id": cls.carrier_tk1.id,
        })
        Rate.create({
            "name": "TK2 NL 1-5 boxes",
            "shipping_class_id": cls.class_tk2.id,
            "country_ids": [(6, 0, [cls.country_nl.id])],
            "unit_type": "box",
            "qty_from": 1, "qty_to": 5,
            "price": 15.0,
            "carrier_id": cls.carrier_tk2.id,
        })
        Rate.create({
            "name": "TK2 NL 6-10 boxes",
            "shipping_class_id": cls.class_tk2.id,
            "country_ids": [(6, 0, [cls.country_nl.id])],
            "unit_type": "box",
            "qty_from": 6, "qty_to": 10,
            "price": 28.0,
            "carrier_id": cls.carrier_tk2.id,
        })
        Rate.create({
            "name": "TK3 NL 1-5 boxes",
            "shipping_class_id": cls.class_tk3.id,
            "country_ids": [(6, 0, [cls.country_nl.id])],
            "unit_type": "box",
            "qty_from": 1, "qty_to": 5,
            "price": 20.0,
            "carrier_id": cls.carrier_tk3.id,
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

    def test_tk1_weight_band_heavy_pallet(self):
        """TK1: product piece weight >= bundle_max_kg → entire TK1 = pallet."""
        # product_tk1_heavy: 25 kg/piece >= 20 kg → pallet
        order = self._create_order([(self.product_tk1_heavy, 3)])
        order.action_d1_compute_transport_cost()

        self.assertIn("PALLETBEREKENING", order.d1_transport_message)
        self.assertIn("25.00 kg/stuk", order.d1_transport_message)
        self.assertTrue(order.d1_pallet_calculation)

    def test_tk1_weight_band_mid_one_per_bundle(self):
        """TK1: mid-band product (max/2..max) → bundles = qty."""
        # product_tk1_mid: 15 kg (>= 10, < 20) → one per bundle
        # 4 pieces → 4 bundles (one-per-bundle), 0 normal
        # Rate: lt_165, 1-10 → 25.00
        order = self._create_order([(self.product_tk1_mid, 4)])
        order.action_d1_compute_transport_cost()

        transport_product = self.env.ref("d1_shipping_cost.product_transport_cost")
        transport_line = order.order_line.filtered(lambda l: l.product_id == transport_product)
        self.assertTrue(transport_line)
        self.assertEqual(transport_line.price_unit, 25.0)
        self.assertIn("één-per-bundel", order.d1_transport_message)
        self.assertIn("4 één-per-bundel + 0 normaal", order.d1_transport_message)

    def test_tk1_weight_band_mixed_pools(self):
        """TK1: mixed order with light + mid-band products → sum of both pools."""
        # product_tk1 (light): 2 kg, 3cm x 3cm, 10 pieces
        #   tubes_per_bundle = floor(15/3)*floor(15/3) = 25
        #   bundles_normal = ceil(10/25) = 1
        #   weight_light = 10*2 = 20 kg, 20/1=20 >= 20 → correction: ceil(20/20) = 1
        # product_tk1_mid (mid): 15 kg, 3 pieces → 3 one-per-bundle
        # total = 1 + 3 = 4 bundles → rate lt_165 1-10 → 25.00
        order = self._create_order([
            (self.product_tk1, 10),
            (self.product_tk1_mid, 3),
        ])
        order.action_d1_compute_transport_cost()

        transport_product = self.env.ref("d1_shipping_cost.product_transport_cost")
        transport_line = order.order_line.filtered(lambda l: l.product_id == transport_product)
        self.assertTrue(transport_line)
        self.assertEqual(transport_line.price_unit, 25.0)
        self.assertIn("3 één-per-bundel + 1 normaal", order.d1_transport_message)

    def test_tk1_uses_order_line_length(self):
        """TK1: max length is taken from order line d1_length, not product."""
        # Product has length 150 cm (< 165 → lt_165 bracket)
        # But order line overrides to 220 (>= 215 → gte_215 bracket)
        # This should use the gte_215 rate (50.00), not lt_165 (25.00)
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": self.product_tk1.id,
            "product_uom_qty": 5,
            "d1_length": 220.0,  # override: product is 150 cm
        })
        order.action_d1_compute_transport_cost()

        transport_product = self.env.ref("d1_shipping_cost.product_transport_cost")
        transport_line = order.order_line.filtered(lambda l: l.product_id == transport_product)
        self.assertTrue(transport_line)
        self.assertEqual(transport_line.price_unit, 50.0,
                         "Should use gte_215 rate based on order line length 220cm")

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
        # 200 couplings * 0.5kg = 100kg, all light band (< 10 kg/piece)
        # ceil(100/20) = 5 boxes, rate 1-5 → 15.00
        order = self._create_order([(self.product_tk2, 200)])
        order.action_d1_compute_transport_cost()

        transport_product = self.env.ref("d1_shipping_cost.product_transport_cost")
        transport_line = order.order_line.filtered(lambda l: l.product_id == transport_product)
        self.assertTrue(transport_line)
        self.assertEqual(transport_line.price_unit, 15.0)

    def test_tk2_pallet_threshold(self):
        """TK2: weight >= threshold → pallet flag."""
        order = self._create_order([(self.product_tk2, 800)])
        order.action_d1_compute_transport_cost()

        self.assertIn("PALLETBEREKENING", order.d1_transport_message)

    def test_tk2_weight_band_heavy_pallet(self):
        """TK2: product piece weight >= box_max_kg → entire TK2 = pallet."""
        # product_tk2_heavy: 22 kg/piece >= 20 kg → pallet
        order = self._create_order([(self.product_tk2_heavy, 2)])
        order.action_d1_compute_transport_cost()

        self.assertIn("PALLETBEREKENING", order.d1_transport_message)
        self.assertIn("22.00 kg/stuk", order.d1_transport_message)
        self.assertTrue(order.d1_pallet_calculation)

    def test_tk2_weight_band_mid_one_per_box(self):
        """TK2: mid-band product (max/2..max) → boxes = qty."""
        # product_tk2_mid: 12 kg (>= 10, < 20) → one per box
        # 3 pieces → 3 boxes (one-per-box), 0 normal
        # Rate: 1-5 → 15.00
        order = self._create_order([(self.product_tk2_mid, 3)])
        order.action_d1_compute_transport_cost()

        transport_product = self.env.ref("d1_shipping_cost.product_transport_cost")
        transport_line = order.order_line.filtered(lambda l: l.product_id == transport_product)
        self.assertTrue(transport_line)
        self.assertEqual(transport_line.price_unit, 15.0)
        self.assertIn("één-per-doos", order.d1_transport_message)
        self.assertIn("3 één-per-doos + 0 normaal", order.d1_transport_message)

    def test_tk2_weight_band_mixed_pools(self):
        """TK2: mixed order with light + mid-band products → sum of both pools."""
        # product_tk2 (light): 0.5 kg, 30 pieces → 15 kg → ceil(15/20) = 1 box normal
        # product_tk2_mid (mid): 12 kg, 2 pieces → 2 boxes one-per-box
        # total = 1 + 2 = 3 boxes → rate 1-5 → 15.00
        order = self._create_order([
            (self.product_tk2, 30),
            (self.product_tk2_mid, 2),
        ])
        order.action_d1_compute_transport_cost()

        transport_product = self.env.ref("d1_shipping_cost.product_transport_cost")
        transport_line = order.order_line.filtered(lambda l: l.product_id == transport_product)
        self.assertTrue(transport_line)
        self.assertEqual(transport_line.price_unit, 15.0)
        self.assertIn("2 één-per-doos + 1 normaal", order.d1_transport_message)

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

    # ------------------------------------------------------------------
    # Qty × Length calculation tests
    # ------------------------------------------------------------------

    def test_tk1_uses_d1_qty_when_use_qty(self):
        """TK1: when d1_use_qty=True, bundle calculation uses d1_qty (piece count)
        instead of product_uom_qty (which is d1_qty × d1_length = total meters).

        Without fix: product_uom_qty=500 → ceil(500/25) = 20 bundles >= max → PALLET
        With fix:    d1_qty=250 → ceil(250/25) = 10 bundles → rate 1-10 → 25.00
        """
        product = self.env["product.product"].create({
            "name": "Test TK1 Use Qty",
            "type": "consu",
            "d1_shipping_class_id": self.class_tk1.id,
            "d1_use_qty": True,
            "d1_use_length": False,
            "d1_length_cm": 200.0,  # 200 cm → line gets 2.0 (/ 100)
            "d1_width_cm": 3.0,
            "d1_height_cm": 3.0,
            "weight": 0.0,  # no weight to avoid weight correction
            "list_price": 10.0,
        })
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        line = self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": product.id,
            "d1_qty": 250,
        })
        # Verify setup: product_uom_qty = 250 * 2.0 = 500
        self.assertEqual(line.product_uom_qty, 500.0)

        order.action_d1_compute_transport_cost()

        # d1_qty=250, tubes_per_bundle = floor(15/3)*floor(15/3) = 25
        # bundles = ceil(250/25) = 10, rate lt_165 1-10 → 25.00
        transport_product = self.env.ref("d1_shipping_cost.product_transport_cost")
        transport_line = order.order_line.filtered(lambda l: l.product_id == transport_product)
        self.assertTrue(transport_line, "Should find rate, NOT pallet")
        self.assertEqual(transport_line.price_unit, 25.0,
                         "Should use d1_qty=250 (10 bundles) not product_uom_qty=500 (20 bundles → pallet)")
        self.assertFalse(order.d1_pallet_calculation,
                         "Should not be pallet when using d1_qty")

    def test_qty_length_use_qty_no_length(self):
        """d1_use_qty=True, d1_use_length=False: length filled from product,
        product_uom_qty = d1_qty * d1_length. Tested via create() (API)."""
        product = self.env["product.product"].create({
            "name": "Test Qty Product",
            "type": "consu",
            "d1_use_qty": True,
            "d1_use_length": False,
            "d1_length_cm": 200.0,
            "list_price": 10.0,
        })
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        line = self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": product.id,
            "d1_qty": 5,
        })
        # Length should be auto-filled from product (200 cm / 100 = 2.0 m)
        self.assertEqual(line.d1_length, 2.0,
                         "d1_length should be product length / 100")
        # product_uom_qty = 5 * 2.0 = 10.0
        self.assertEqual(line.product_uom_qty, 10.0,
                         "product_uom_qty should be d1_qty * d1_length")

    def test_qty_length_use_qty_and_length(self):
        """d1_use_qty=True, d1_use_length=True: d1_length stays as entered,
        product_uom_qty = d1_qty * d1_length."""
        product = self.env["product.product"].create({
            "name": "Test Qty+Length Product",
            "type": "consu",
            "d1_use_qty": True,
            "d1_use_length": True,
            "d1_length_cm": 200.0,
            "list_price": 10.0,
        })
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        line = self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": product.id,
            "d1_qty": 3,
            "d1_length": 150.0,  # user override, NOT from product
        })
        # Length should stay at user-entered value
        self.assertEqual(line.d1_length, 150.0,
                         "d1_length should stay as user entered (not product)")
        # product_uom_qty = 3 * 150 = 450
        self.assertEqual(line.product_uom_qty, 450.0,
                         "product_uom_qty should be d1_qty * d1_length")

    def test_qty_length_no_use_qty(self):
        """d1_use_qty=False: product_uom_qty stays untouched."""
        product = self.env["product.product"].create({
            "name": "Test Normal Product",
            "type": "consu",
            "d1_use_qty": False,
            "d1_length_cm": 200.0,
            "list_price": 10.0,
        })
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        line = self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": product.id,
            "product_uom_qty": 7,
        })
        # product_uom_qty should stay at manually entered value
        self.assertEqual(line.product_uom_qty, 7.0,
                         "product_uom_qty should not be altered")

    def test_qty_length_write_recalculates(self):
        """Writing d1_qty on an existing line recalculates product_uom_qty."""
        product = self.env["product.product"].create({
            "name": "Test Write Qty Product",
            "type": "consu",
            "d1_use_qty": True,
            "d1_use_length": False,
            "d1_length_cm": 100.0,
            "list_price": 10.0,
        })
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        line = self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": product.id,
            "d1_qty": 2,
        })
        # 100 cm / 100 = 1.0; 2 * 1.0 = 2.0
        self.assertEqual(line.product_uom_qty, 2.0)

        # Write a new d1_qty
        line.write({"d1_qty": 10})
        # 10 * 1.0 = 10.0
        self.assertEqual(line.product_uom_qty, 10.0,
                         "product_uom_qty should recalculate after write")

    # ------------------------------------------------------------------
    # Carrier (transporteur) determination tests
    # ------------------------------------------------------------------

    def test_carrier_tk1_only(self):
        """Carrier is set from TK1 rate when only TK1 products in order."""
        order = self._create_order([(self.product_tk1, 10)])
        order.action_d1_compute_transport_cost()

        self.assertEqual(order.carrier_id, self.carrier_tk1,
                         "Carrier should be TK1 carrier")
        self.assertIn("Transporteur", order.d1_transport_message)

    def test_carrier_tk2_only(self):
        """Carrier is set from TK2 rate when only TK2 products in order."""
        order = self._create_order([(self.product_tk2, 30)])
        order.action_d1_compute_transport_cost()

        self.assertEqual(order.carrier_id, self.carrier_tk2,
                         "Carrier should be TK2 carrier")

    def test_carrier_tk3_only(self):
        """Carrier is set from TK3 rate when only TK3 products in order."""
        order = self._create_order([(self.product_tk3_small, 5)])
        order.action_d1_compute_transport_cost()

        self.assertEqual(order.carrier_id, self.carrier_tk3,
                         "Carrier should be TK3 carrier")

    def test_carrier_priority_tk1_over_tk2(self):
        """Mixed TK1 + TK2: carrier comes from TK1 (priority TK1 > TK2)."""
        order = self._create_order([
            (self.product_tk1, 10),
            (self.product_tk2, 30),
        ])
        order.action_d1_compute_transport_cost()

        self.assertEqual(order.carrier_id, self.carrier_tk1,
                         "Carrier should be TK1 (priority TK1 > TK2)")

    def test_carrier_priority_tk3_over_tk2(self):
        """Mixed TK3 + TK2: carrier comes from TK3 (priority TK3 > TK2)."""
        order = self._create_order([
            (self.product_tk3_small, 5),
            (self.product_tk2, 30),
        ])
        order.action_d1_compute_transport_cost()

        self.assertEqual(order.carrier_id, self.carrier_tk3,
                         "Carrier should be TK3 (priority TK3 > TK2)")

    def test_carrier_priority_tk1_over_tk3(self):
        """Mixed TK1 + TK3: carrier comes from TK1 (priority TK1 > TK3)."""
        order = self._create_order([
            (self.product_tk1, 10),
            (self.product_tk3_small, 5),
        ])
        order.action_d1_compute_transport_cost()

        self.assertEqual(order.carrier_id, self.carrier_tk1,
                         "Carrier should be TK1 (priority TK1 > TK3)")

    def test_carrier_fallback_on_pallet(self):
        """When TK1 goes to pallet (no rate), carrier falls through to next class."""
        # TK1 heavy → pallet (no rate, no carrier)
        # TK2 light → rate found → TK2 carrier
        order = self._create_order([
            (self.product_tk1_heavy, 3),
            (self.product_tk2, 30),
        ])
        order.action_d1_compute_transport_cost()

        self.assertEqual(order.carrier_id, self.carrier_tk2,
                         "Should fall through to TK2 carrier when TK1 is pallet")

    def test_carrier_empty_no_classes(self):
        """No shipping classes in order → carrier stays empty."""
        order = self._create_order([(self.product_no_class, 10)])
        order.action_d1_compute_transport_cost()

        self.assertFalse(order.carrier_id,
                         "No carrier when no shipping classes in order")

    # ------------------------------------------------------------------
    # Skip calculation when customer has a fixed delivery method
    # ------------------------------------------------------------------

    def test_skip_when_partner_carrier_set(self):
        """Partner with property_delivery_carrier_id → calculation skipped."""
        self.partner.property_delivery_carrier_id = self.carrier_tk1
        order = self._create_order([(self.product_tk1, 50)])
        order.action_d1_compute_transport_cost()

        # Message reflects the skip, not a TK calculation
        self.assertIn("skipped", order.d1_transport_message)
        self.assertIn(self.carrier_tk1.display_name, order.d1_transport_message)
        self.assertNotIn("TK1:", order.d1_transport_message)

        # No transport cost line is created when skipping
        transport_line = order.order_line.filtered(
            lambda l: "[TRANSPORT]" in (l.name or "")
        )
        self.assertFalse(transport_line, "No transport line when skipped")

    def test_no_skip_when_partner_carrier_empty(self):
        """Partner without property_delivery_carrier_id → normal calculation runs."""
        self.partner.property_delivery_carrier_id = False
        order = self._create_order([(self.product_tk1, 50)])
        order.action_d1_compute_transport_cost()

        self.assertIn("TK1", order.d1_transport_message)
        self.assertNotIn("skipped", order.d1_transport_message)
