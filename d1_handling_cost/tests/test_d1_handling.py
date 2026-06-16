import logging

from odoo.tests.common import TransactionCase, tagged

_logger = logging.getLogger(__name__)


@tagged("d1_handling_cost", "-at_install", "post_install")
class TestD1Handling(TransactionCase):
    """Smoke-tests for d1.handling, d1.handling.line and the automated
    handling cost line on sale orders."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.currency = cls.env.ref("base.EUR")
        cls.product_template = cls.env["product.template"].create({
            "name": "Handling Fee Product",
            "type": "service",
            "list_price": 0.0,
        })
        cls.handling = cls.env["d1.handling"].create({
            "name": "Test Handling",
            "currency_id": cls.currency.id,
            "product_id": cls.product_template.id,
        })
        cls.line_low = cls.env["d1.handling.line"].create({
            "handling_id": cls.handling.id,
            "name": "0-500",
            "sequence": 10,
            "value_from": 0.0,
            "total": 500.0,
            "amount": 25.0,
        })
        cls.line_high = cls.env["d1.handling.line"].create({
            "handling_id": cls.handling.id,
            "name": "500-2000",
            "sequence": 20,
            "value_from": 500.0,
            "total": 2000.0,
            "amount": 15.0,
        })
        cls.partner = cls.env["res.partner"].create({
            "name": "Test Customer",
            "d1_handling_id": cls.handling.id,
        })
        # A regular product for order lines
        cls.regular_product = cls.env["product.product"].create({
            "name": "Widget",
            "type": "consu",
            "list_price": 100.0,
        })

    # ------------------------------------------------------------------
    # Model smoke-tests
    # ------------------------------------------------------------------
    def test_handling_create(self):
        """d1.handling record is created with correct defaults."""
        self.assertTrue(self.handling.active)
        self.assertEqual(self.handling.sequence, 10)
        self.assertEqual(self.handling.currency_id, self.currency)

    def test_handling_line_create(self):
        """d1.handling.line records are linked to the handling."""
        self.assertEqual(len(self.handling.line_ids), 2)
        self.assertEqual(self.line_low.amount, 25.0)
        self.assertEqual(self.line_high.value_from, 500.0)

    def test_partner_handling_link(self):
        """res.partner.d1_handling_id links to the handling."""
        self.assertEqual(self.partner.d1_handling_id, self.handling)

    # ------------------------------------------------------------------
    # Automation logic tests
    # ------------------------------------------------------------------
    def _create_draft_order(self, qty=1, price_unit=100.0):
        """Helper: create a draft sale order with one regular product line."""
        order = self.env["sale.order"].create({
            "partner_id": self.partner.id,
        })
        self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": self.regular_product.id,
            "product_uom_qty": qty,
            "price_unit": price_unit,
        })
        return order

    def test_apply_handling_adds_line(self):
        """_d1_apply_handling adds a handling line matching the low bracket."""
        order = self._create_draft_order(qty=1, price_unit=200.0)
        order._d1_apply_handling()

        handling_lines = order.order_line.filtered(
            lambda l: l.product_template_id == self.product_template
        )
        self.assertEqual(len(handling_lines), 1)
        self.assertEqual(handling_lines.price_unit, 25.0)

    def test_apply_handling_updates_bracket(self):
        """When order amount changes bracket, price_unit is updated."""
        order = self._create_draft_order(qty=1, price_unit=200.0)
        order._d1_apply_handling()

        # Increase amount to move into the high bracket (500–2000)
        order.order_line.filtered(
            lambda l: l.product_template_id != self.product_template
        ).write({"price_unit": 600.0})
        order._d1_apply_handling()

        handling_lines = order.order_line.filtered(
            lambda l: l.product_template_id == self.product_template
        )
        self.assertEqual(handling_lines.price_unit, 15.0)

    def test_apply_handling_removes_line(self):
        """When no bracket matches, existing handling line is removed."""
        order = self._create_draft_order(qty=1, price_unit=200.0)
        order._d1_apply_handling()

        # Move amount above all brackets (> 2000)
        order.order_line.filtered(
            lambda l: l.product_template_id != self.product_template
        ).write({"price_unit": 3000.0})
        order._d1_apply_handling()

        handling_lines = order.order_line.filtered(
            lambda l: l.product_template_id == self.product_template
        )
        self.assertEqual(len(handling_lines), 0)

    def test_apply_handling_no_handling_on_partner(self):
        """Orders for partners without handling get no handling line."""
        partner_no_handling = self.env["res.partner"].create({
            "name": "No Handling Customer",
        })
        order = self.env["sale.order"].create({
            "partner_id": partner_no_handling.id,
        })
        self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": self.regular_product.id,
            "product_uom_qty": 1,
            "price_unit": 200.0,
        })
        order._d1_apply_handling()

        handling_lines = order.order_line.filtered(
            lambda l: l.product_template_id == self.product_template
        )
        self.assertEqual(len(handling_lines), 0)

    def test_apply_handling_skips_non_draft(self):
        """_d1_apply_handling does nothing for confirmed orders."""
        # Create a partner without handling so no handling line is added
        partner_no_handling = self.env["res.partner"].create({
            "name": "Confirm Test Customer",
        })
        order = self.env["sale.order"].create({
            "partner_id": partner_no_handling.id,
        })
        self.env["sale.order.line"].create({
            "order_id": order.id,
            "product_id": self.regular_product.id,
            "product_uom_qty": 1,
            "price_unit": 200.0,
        })
        order.action_confirm()
        # Now assign the handling partner and call — should skip (not draft)
        order.partner_id = self.partner
        order._d1_apply_handling()

        handling_lines = order.order_line.filtered(
            lambda l: l.product_template_id == self.product_template
        )
        self.assertEqual(len(handling_lines), 0)
