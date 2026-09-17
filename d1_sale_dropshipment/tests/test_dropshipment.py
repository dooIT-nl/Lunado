from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "d1_sale_dropshipment")
class TestD1SaleDropshipment(TransactionCase):
    """Smoke tests voor de dropshipment-vlag (Studio-conversie C2)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dropship_partner = cls.env["res.partner"].create(
            {"name": "D1 Dropship klant", "d1_dropshipment": True}
        )
        cls.normal_partner = cls.env["res.partner"].create(
            {"name": "D1 Gewone klant"}
        )

    def test_01_flag_copied_on_create(self):
        """Vlag van de klant komt mee bij aanmaken (ook via API/create)."""
        order = self.env["sale.order"].create(
            {"partner_id": self.dropship_partner.id}
        )
        self.assertTrue(order.d1_dropshipment)
        order2 = self.env["sale.order"].create(
            {"partner_id": self.normal_partner.id}
        )
        self.assertFalse(order2.d1_dropshipment)

    def test_02_flag_follows_partner_change(self):
        """Wijzigen van de klant werkt de vlag bij."""
        order = self.env["sale.order"].create(
            {"partner_id": self.normal_partner.id}
        )
        self.assertFalse(order.d1_dropshipment)
        order.partner_id = self.dropship_partner
        self.assertTrue(order.d1_dropshipment)

    def test_03_manual_override_allowed(self):
        """Handmatige aanpassing per order blijft mogelijk."""
        order = self.env["sale.order"].create(
            {"partner_id": self.dropship_partner.id}
        )
        order.d1_dropshipment = False
        self.assertFalse(order.d1_dropshipment)
        # explicit waarde bij create wint van de compute
        order2 = self.env["sale.order"].create(
            {"partner_id": self.normal_partner.id, "d1_dropshipment": True}
        )
        self.assertTrue(order2.d1_dropshipment)
