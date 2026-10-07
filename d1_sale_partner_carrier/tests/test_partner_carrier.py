from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "d1_sale_partner_carrier")
class TestD1SalePartnerCarrier(TransactionCase):
    """Smoke tests: leveringswijze van de klant voorvullen op de order."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        shipping_product = cls.env["product.product"].create(
            {"name": "D1 Verzendkosten", "type": "service",
             "list_price": 9.5}
        )
        cls.carrier_a = cls.env["delivery.carrier"].create(
            {"name": "D1 Koerier A", "delivery_type": "fixed",
             "fixed_price": 9.5, "product_id": shipping_product.id}
        )
        cls.carrier_b = cls.env["delivery.carrier"].create(
            {"name": "D1 Koerier B", "delivery_type": "fixed",
             "fixed_price": 19.5, "product_id": shipping_product.id}
        )
        cls.partner_with = cls.env["res.partner"].create(
            {"name": "D1 Klant met koerier",
             "property_delivery_carrier_id": cls.carrier_a.id}
        )
        # expliciet leeg: demodata zet via ir.default anders een standaard
        # leveringswijze op elke nieuwe partner
        cls.partner_without = cls.env["res.partner"].create(
            {"name": "D1 Klant zonder koerier",
             "property_delivery_carrier_id": False}
        )

    def test_01_carrier_prefilled_on_create(self):
        """Klant met standaard leveringswijze -> carrier voorgevuld
        (API-pad: kale create zonder onchanges)."""
        order = self.env["sale.order"].create(
            {"partner_id": self.partner_with.id}
        )
        self.assertEqual(order.carrier_id, self.carrier_a)

    def test_02_no_carrier_on_partner(self):
        """Klant zonder standaard leveringswijze -> veld blijft leeg."""
        order = self.env["sale.order"].create(
            {"partner_id": self.partner_without.id}
        )
        self.assertFalse(order.carrier_id)

    def test_03_manual_choice_sticks(self):
        """Handmatige keuze (of de verzendkosten-wizard) blijft staan zolang
        het afleveradres niet wijzigt."""
        order = self.env["sale.order"].create(
            {"partner_id": self.partner_with.id}
        )
        order.carrier_id = self.carrier_b
        order.note = "regel-wijziging die geen herberekening mag triggeren"
        self.assertEqual(order.carrier_id, self.carrier_b)

    def test_04_partner_change_updates_carrier(self):
        """Ander afleveradres met eigen voorkeur -> carrier volgt; adres
        zonder voorkeur -> bestaande keuze blijft staan."""
        order = self.env["sale.order"].create(
            {"partner_id": self.partner_without.id}
        )
        order.carrier_id = self.carrier_b
        order.partner_shipping_id = self.partner_with
        self.assertEqual(order.carrier_id, self.carrier_a)
        order.partner_shipping_id = self.partner_without
        self.assertEqual(
            order.carrier_id, self.carrier_a,
            "zonder voorkeur op het nieuwe adres niet leegmaken",
        )

    def test_05_contact_falls_back_to_commercial_partner(self):
        """Afleveradres zonder eigen voorkeur -> voorkeur van de
        commerciele partner (zelfde terugval als de wizard)."""
        contact = self.env["res.partner"].create(
            {"name": "D1 Afleveradres", "type": "delivery",
             "parent_id": self.partner_with.id,
             "property_delivery_carrier_id": False}
        )
        order = self.env["sale.order"].create(
            {"partner_id": self.partner_with.id,
             "partner_shipping_id": contact.id}
        )
        self.assertEqual(order.carrier_id, self.carrier_a)
