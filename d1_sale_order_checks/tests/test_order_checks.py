from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "d1_sale_order_checks")
class TestD1SaleOrderChecks(TransactionCase):
    """Smoke tests voor de verkoopordercontroles (Studio-conversie C1)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env["res.partner"].create(
            {"name": "D1 Klant", "d1_rel_type": "customer"}
        )
        cls.prospect = cls.env["res.partner"].create(
            {"name": "D1 Prospect", "d1_rel_type": "prospect"}
        )
        cls.product = cls.env["product.product"].create(
            {"name": "D1 Checks product", "list_price": 100.0}
        )

    def _create_order(self, partner, **vals):
        return self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "order_line": [
                    (0, 0, {"product_id": self.product.id, "product_uom_qty": 1})
                ],
                **vals,
            }
        )

    def test_01_prospect_blocked(self):
        """Order voor een prospect wordt geblokkeerd (aanmaken en wijzigen)."""
        with self.assertRaises(ValidationError):
            self._create_order(self.prospect)
        order = self._create_order(self.customer)
        with self.assertRaises(ValidationError):
            order.partner_id = self.prospect

    def test_02_customer_allowed(self):
        """Order voor klant (of relatie zonder type) is toegestaan."""
        self._create_order(self.customer)
        no_type = self.env["res.partner"].create({"name": "D1 Zonder type"})
        self._create_order(no_type)

    def test_03_duplicate_client_order_ref_blocked(self):
        """Dubbele klantreferentie bij dezelfde klant wordt geblokkeerd."""
        self._create_order(self.customer, client_order_ref="REF-001")
        with self.assertRaises(ValidationError):
            self._create_order(self.customer, client_order_ref="REF-001")
        # Andere klant mag dezelfde referentie gebruiken
        other = self.env["res.partner"].create({"name": "D1 Andere klant"})
        self._create_order(other, client_order_ref="REF-001")
        # Zelfde klant, andere referentie mag
        self._create_order(self.customer, client_order_ref="REF-002")

    def test_04_credit_limit_blocks_confirmation(self):
        """Overschreden kredietlimiet blokkeert bevestigen; vinkje staat
        bevestiging toe."""
        self.customer.credit_limit = 50.0
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.customer.id,
                "invoice_line_ids": [
                    (0, 0, {
                        "name": "D1 openstaande post",
                        "quantity": 1,
                        "price_unit": 500.0,
                    })
                ],
            }
        )
        invoice.action_post()
        self.assertGreater(self.customer.credit, self.customer.credit_limit)
        order = self._create_order(self.customer)
        self.assertTrue(order.d1_credit_limit_exceeded)
        with self.assertRaises(UserError):
            order.action_confirm()
        order.d1_exceed_credit_limit = True
        order.action_confirm()
        self.assertEqual(order.state, "sale")

    def test_05_no_credit_limit_no_block(self):
        """Zonder kredietlimiet (0) wordt niets geblokkeerd."""
        self.customer.credit_limit = 0.0
        order = self._create_order(self.customer)
        self.assertFalse(order.d1_credit_limit_exceeded)
        order.action_confirm()
        self.assertEqual(order.state, "sale")

    def test_06_insurance_fields(self):
        """Smoke: kredietverzekering-velden zijn instelbaar."""
        self.customer.write(
            {
                "d1_credit_insurance": "insured_insurer",
                "d1_insured_amount": 25000.0,
            }
        )
        self.assertEqual(self.customer.d1_credit_insurance, "insured_insurer")
