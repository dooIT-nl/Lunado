from datetime import timedelta

from freezegun import freeze_time

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

# Monday 10:00 UTC — a fixed, deterministic base for all tests, because the
# working-day rounding makes results depend on the day of the week.
FROZEN_NOW = "2026-09-14 10:00:00"


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
        cls.supplier_location = cls.env.ref("stock.stock_location_suppliers")

    def _create_order(self, lines, partner=None):
        return self.env["sale.order"].create(
            {
                "partner_id": (partner or self.partner).id,
                "warehouse_id": self.warehouse.id,
                "order_line": [
                    (0, 0, {"product_id": product.id, "product_uom_qty": qty})
                    for product, qty in lines
                ],
            }
        )

    def _create_receipt(self, product, qty, scheduled):
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": self.warehouse.in_type_id.id,
                "location_id": self.supplier_location.id,
                "location_dest_id": self.warehouse.lot_stock_id.id,
                "scheduled_date": scheduled,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_uom_qty": qty,
                            "location_id": self.supplier_location.id,
                            "location_dest_id": self.warehouse.lot_stock_id.id,
                        },
                    )
                ],
            }
        )
        picking.action_confirm()
        return picking

    def _assert_close(self, actual, expected, msg=None):
        self.assertTrue(actual, msg or "commitment_date is niet gezet")
        self.assertAlmostEqual(
            actual, expected, delta=timedelta(minutes=5), msg=msg
        )

    @freeze_time(FROZEN_NOW)
    def test_01_sufficient_stock_no_sale_delay(self):
        """Voldoende voorraad -> leverdatum vandaag, sale_delay genegeerd."""
        order = self._create_order([(self.product_stock, 5)])
        self._assert_close(
            order.commitment_date,
            fields.Datetime.now(),
            "Met voldoende voorraad mag de sale_delay niet meetellen",
        )

    @freeze_time(FROZEN_NOW)
    def test_02_no_stock_no_picking_uses_sale_delay(self):
        """Geen voorraad en geen ontvangst -> nu + sale_delay."""
        order = self._create_order([(self.product_no_stock, 5)])
        self._assert_close(
            order.commitment_date,
            fields.Datetime.now() + timedelta(days=7),
        )

    @freeze_time(FROZEN_NOW)
    def test_03_no_stock_with_incoming_picking(self):
        """Geen voorraad, wel geplande ontvangst -> scheduled_date picking."""
        scheduled = fields.Datetime.now() + timedelta(days=30)
        self._create_receipt(self.product_no_stock, 50, scheduled)
        order = self._create_order([(self.product_no_stock, 5)])
        self._assert_close(order.commitment_date, scheduled)

    @freeze_time(FROZEN_NOW)
    def test_04_order_takes_latest_line_date(self):
        """Laatste regeldatum bepaalt de leverdatum van de order."""
        order = self._create_order(
            [(self.product_stock, 5), (self.product_no_stock, 5)]
        )
        self._assert_close(
            order.commitment_date,
            fields.Datetime.now() + timedelta(days=7),
        )

    @freeze_time(FROZEN_NOW)
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
        self._assert_close(
            order.commitment_date,
            fields.Datetime.now() + timedelta(days=7),
            "Kitcomponent zonder voorraad moet sale_delay component volgen",
        )

    @freeze_time(FROZEN_NOW)
    def test_06_customer_request_date(self):
        """Latere klantdatum wint; eerdere klantdatum geeft waarschuwing."""
        order = self._create_order([(self.product_no_stock, 5)])
        # +60 dagen vanaf maandag = vrijdag: geen werkdag-verschuiving
        later = fields.Datetime.now() + timedelta(days=60)
        order.d1_customer_request_date = later
        self.assertEqual(order.commitment_date, later)
        self.assertFalse(order.d1_delivery_date_warning)
        earlier = fields.Datetime.now() + timedelta(days=1)
        order.d1_customer_request_date = earlier
        self.assertTrue(order.d1_delivery_date_warning)
        self.assertNotEqual(order.commitment_date, earlier)

    @freeze_time(FROZEN_NOW)
    def test_07_confirmed_demand_reduces_available_stock(self):
        """LUN-1: bevestigde uitgaande vraag telt niet als beschikbaar."""
        # Bevestigde order claimt 96 van de 100 -> 4 beschikbaar
        claim = self._create_order([(self.product_stock, 96)])
        claim.action_confirm()
        order = self._create_order([(self.product_stock, 5)])
        self._assert_close(
            order.commitment_date,
            fields.Datetime.now() + timedelta(days=10),
            "Bevestigde vraag moet van de beschikbare voorraad af",
        )

    @freeze_time(FROZEN_NOW)
    def test_08_past_receipt_clamped_to_today(self):
        """LUN-3: ontvangst met datum in het verleden -> vandaag."""
        scheduled = fields.Datetime.now() - timedelta(days=5)
        self._create_receipt(self.product_no_stock, 50, scheduled)
        order = self._create_order([(self.product_no_stock, 5)])
        self._assert_close(
            order.commitment_date,
            fields.Datetime.now(),
            "Verlate ontvangst mag geen leverdatum in het verleden geven",
        )

    @freeze_time(FROZEN_NOW)
    def test_09_weekend_rounds_to_monday(self):
        """LUN-9: datum in het weekend schuift door naar maandag."""
        product = self.env["product.product"].create(
            {
                "name": "D1 Product zaterdaglevering",
                "is_storable": True,
                "sale_delay": 5,  # maandag + 5 = zaterdag
            }
        )
        order = self._create_order([(product, 5)])
        self._assert_close(
            order.commitment_date,
            fields.Datetime.now() + timedelta(days=7),  # -> maandag
            "Zaterdag moet doorschuiven naar maandag",
        )

    @freeze_time(FROZEN_NOW)
    def test_10_customer_cutoff_shifts_to_next_day(self):
        """LUN-10: na de cutoff-tijd van de klant -> volgende werkdag."""
        partner = self.env["res.partner"].create(
            {"name": "D1 Klant met cutoff", "d1_delivery_cutoff_hour": 8.0}
        )
        order = self._create_order([(self.product_stock, 5)], partner=partner)
        # Berekend moment (ma 10:00) ligt na cutoff 08:00 -> dinsdag
        self._assert_close(
            order.commitment_date,
            fields.Datetime.now() + timedelta(days=1),
            "Na cutoff moet de levering naar de volgende werkdag",
        )
