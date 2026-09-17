from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "d1_purchase_partner_delivery")
class TestD1PurchasePartnerDelivery(TransactionCase):
    """Smoke tests voor leverdefaults van de leverancier (conversie C3)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.receipt_type = cls.warehouse.in_type_id
        cls.other_type = cls.env["stock.picking.type"].create(
            {
                "name": "D1 Speciale ontvangst",
                "code": "incoming",
                "sequence_code": "D1IN",
                "warehouse_id": cls.warehouse.id,
            }
        )
        cls.excluded_type = cls.env["stock.picking.type"].create(
            {
                "name": "D1 Dropship-achtig",
                "code": "incoming",
                "sequence_code": "D1DS",
                "warehouse_id": cls.warehouse.id,
                "d1_no_partner_delivery_default": True,
            }
        )
        cls.incoterm = cls.env["account.incoterms"].search([], limit=1)
        cls.vendor = cls.env["res.partner"].create(
            {
                "name": "D1 Leverancier",
                "d1_delivery_picking_type_id": cls.other_type.id,
                "d1_incoterm_id": cls.incoterm.id,
            }
        )
        cls.vendor_plain = cls.env["res.partner"].create(
            {"name": "D1 Leverancier zonder defaults"}
        )
        cls.product = cls.env["product.product"].create(
            {"name": "D1 Inkoopproduct", "purchase_ok": True}
        )

    def _create_po(self, partner, **vals):
        return self.env["purchase.order"].create(
            {
                "partner_id": partner.id,
                "order_line": [
                    (0, 0, {"product_id": self.product.id, "product_qty": 1})
                ],
                **vals,
            }
        )

    def test_01_defaults_applied_on_create(self):
        """Leverdefaults van de leverancier komen mee bij aanmaken."""
        po = self._create_po(self.vendor)
        self.assertEqual(po.picking_type_id, self.other_type)
        self.assertEqual(po.incoterm_id, self.incoterm)

    def test_02_no_defaults_no_change(self):
        """Zonder leverdefaults blijft het standaard operatietype staan."""
        po = self._create_po(self.vendor_plain)
        self.assertEqual(po.picking_type_id, self.receipt_type)

    def test_03_excluded_type_not_overridden(self):
        """Uitgesloten operatietype (Dropship-vinkje) wordt niet overschreven."""
        po = self._create_po(
            self.vendor, picking_type_id=self.excluded_type.id
        )
        self.assertEqual(po.picking_type_id, self.excluded_type)
        self.assertFalse(po.incoterm_id)

    def test_04_partner_change_applies_defaults(self):
        """Wisselen van leverancier past de defaults opnieuw toe."""
        po = self._create_po(self.vendor_plain)
        self.assertEqual(po.picking_type_id, self.receipt_type)
        po.partner_id = self.vendor
        self.assertEqual(po.picking_type_id, self.other_type)
        self.assertEqual(po.incoterm_id, self.incoterm)

    def test_05_confirmed_order_untouched(self):
        """Bevestigde orders worden niet meer aangepast."""
        po = self._create_po(self.vendor_plain)
        po.button_confirm()
        po.partner_id = self.vendor
        self.assertEqual(po.picking_type_id, self.receipt_type)
