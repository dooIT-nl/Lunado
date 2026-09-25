from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "d1_framecalculator")
class TestD1Framecalculator(TransactionCase):
    """Smoke tests voor de framecalculator-knop en -instellingen."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "D1 Frame klant"})
        cls.order = cls.env["sale.order"].create(
            {"partner_id": cls.partner.id}
        )
        cls.params = cls.env["ir.config_parameter"].sudo()

    def test_01_not_configured_raises(self):
        """Zonder configuratie geeft de knop een duidelijke melding."""
        self.params.set_param("d1_framecalculator.url", "")
        self.params.set_param("d1_framecalculator.api_key", "")
        with self.assertRaises(UserError):
            self.order.action_d1_open_framecalculator()

    def test_02_url_built_with_encoded_key(self):
        """URL bevat orderid/customerid en de key wordt URL-encoded."""
        self.params.set_param(
            "d1_framecalculator.url", "https://calc.example.com/"
        )
        # platte key met tekens die encoding vereisen (+, =)
        self.params.set_param("d1_framecalculator.api_key", "abc+def=")
        action = self.order.action_d1_open_framecalculator()
        self.assertEqual(action["type"], "ir.actions.act_url")
        self.assertEqual(action["target"], "self")
        url = action["url"]
        self.assertTrue(url.startswith("https://calc.example.com?"))
        self.assertIn("apikey=abc%2Bdef%3D", url)
        self.assertIn("orderid=%s" % self.order.id, url)
        self.assertIn("customerid=%s" % self.partner.id, url)

    def test_03_settings_fields_store_params(self):
        """Instellingen schrijven naar de systeemparameters."""
        settings = self.env["res.config.settings"].create(
            {
                "d1_framecalculator_url": "https://calc.example.com",
                "d1_framecalculator_api_key": "sleutel123",
            }
        )
        settings.execute()
        self.assertEqual(
            self.params.get_param("d1_framecalculator.url"),
            "https://calc.example.com",
        )
        self.assertEqual(
            self.params.get_param("d1_framecalculator.api_key"), "sleutel123"
        )
