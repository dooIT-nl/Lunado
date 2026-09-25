from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "d1_product_partner_data")
class TestD1ProductPartnerData(TransactionCase):
    """Smoke tests voor de stamdatavelden (Studio-conversie C7)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "D1 Stamdata product",
                "is_storable": True,
                "d1_abc_code": "05",
                "d1_courant": True,
                "d1_cost_calc": 12.34,
            }
        )

    def test_01_master_data_fields(self):
        """Smoke: stamdatavelden zijn instelbaar."""
        self.assertEqual(self.product.d1_abc_code, "05")
        self.assertTrue(self.product.d1_courant)
        self.assertAlmostEqual(self.product.d1_cost_calc, 12.34)

    def test_02_available_follows_stock(self):
        """Beschikbaar = voorraad > 0 (bug uit Studio-versie gefixt)."""
        template = self.product.product_tmpl_id
        self.assertFalse(template.d1_available)
        self.env["stock.quant"]._update_available_quantity(
            self.product, self.warehouse.lot_stock_id, 10
        )
        template.invalidate_recordset()
        template._compute_d1_available()
        self.assertTrue(template.d1_available)

    def test_03_available_false_for_subcontract_bom(self):
        """Product met subcontract-stuklijst is nooit beschikbaar."""
        bom_type_field = self.env["mrp.bom"]._fields["type"]
        selection_values = [
            value for value, _label in bom_type_field.selection
        ]
        if "subcontract" not in selection_values:
            self.skipTest("mrp_subcontracting niet geinstalleerd")
        product = self.env["product.product"].create(
            {"name": "D1 Uitbesteed product", "is_storable": True}
        )
        self.env["stock.quant"]._update_available_quantity(
            product, self.warehouse.lot_stock_id, 10
        )
        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": product.product_tmpl_id.id,
                "type": "subcontract",
                "product_qty": 1,
            }
        )
        self.assertFalse(product.product_tmpl_id.d1_available)

    def test_04_package_count(self):
        """Aantal verpakkingen = aantal verpakkings-UoM's."""
        template = self.product.product_tmpl_id
        self.assertEqual(template.d1_package_count, len(template.uom_ids))

    def test_05_delivery_note_url(self):
        """Smoke: pakbon-URL is instelbaar op de order."""
        partner = self.env["res.partner"].create({"name": "D1 URL klant"})
        order = self.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "d1_delivery_note_url": "https://example.com/pakbon/1",
            }
        )
        self.assertTrue(order.d1_delivery_note_url.startswith("https://"))

    def test_06_stale_studio_field_row_cleanup(self):
        """De eindschoonmaak verwijdert wees-veldrijen (metadata zonder
        registerveld) en laat levende registervelden ongemoeid."""
        from odoo.addons.d1_product_partner_data import hooks

        # simuleer een achtergebleven gedelegeerde veldrij (state 'base',
        # geen veld in het register) zoals _inherits die achterlaat
        model_id = self.env["ir.model"]._get_id("product.product")
        self.env.cr.execute(
            """
            INSERT INTO ir_model_fields
                (model_id, model, name, field_description, ttype, state,
                 copied, store, required, readonly, index, translate,
                 company_dependent)
            VALUES (%s, 'product.product', 'x_studio_stale_test',
                    '{"en_US": "Stale test"}', 'boolean', 'base',
                    false, false, false, false, false, false, false)
            RETURNING id
            """,
            (model_id,),
        )
        stale_id = self.env.cr.fetchone()[0]

        hooks._remove_stale_studio_field_rows(self.env)

        self.env.cr.execute(
            "SELECT 1 FROM ir_model_fields WHERE id = %s", (stale_id,)
        )
        self.assertFalse(self.env.cr.fetchone(),
                         "wees-veldrij moet verwijderd zijn")

        # delegaties met een levende ouderrij (bv. d1_studio_compat-aliassen
        # op product.template) mogen niet worden geraakt
        self.env.cr.execute(
            r"SELECT name FROM ir_model_fields "
            r"WHERE model = 'product.template' AND name LIKE 'x\_studio\_%'"
        )
        for (name,) in self.env.cr.fetchall():
            self.env.cr.execute(
                "SELECT 1 FROM ir_model_fields "
                "WHERE model = 'product.product' AND name = %s",
                (name,),
            )
            self.assertTrue(
                self.env.cr.fetchone(),
                "delegatie %s met levende ouder mag niet verwijderd zijn"
                % name,
            )

    def test_07_handling_model_cleanup(self):
        """De eindschoonmaak verwijdert handmatige Studio-modellen inclusief
        velden, views en tabellen — ook met de afhankelijkheidsketen van de
        echte Handling-matrix (related x_currency_id via x_handling_id naar
        de valuta van het hoofdmodel, bevinding go-live-rehearsal 25-09)."""
        from odoo.addons.d1_product_partner_data import hooks

        parent_name = "x_d1_test_handling"
        line_name = "x_d1_test_handling_line"
        parent = self.env["ir.model"].create(
            {"name": "D1 Test Handling", "model": parent_name,
             "state": "manual"}
        )
        line = self.env["ir.model"].create(
            {"name": "D1 Test Handling Line", "model": line_name,
             "state": "manual"}
        )
        self.env["ir.model.fields"].create(
            {"model_id": parent.id, "name": "x_studio_currency_id",
             "field_description": "Valuta", "ttype": "many2one",
             "relation": "res.currency", "state": "manual"}
        )
        self.env["ir.model.fields"].create(
            {"model_id": line.id, "name": "x_handling_id",
             "field_description": "Handling", "ttype": "many2one",
             "relation": parent_name, "state": "manual"}
        )
        self.env["ir.model.fields"].create(
            {"model_id": line.id, "name": "x_currency_id",
             "field_description": "Valuta", "ttype": "many2one",
             "relation": "res.currency", "state": "manual",
             "related": "x_handling_id.x_studio_currency_id"}
        )
        # monetary hangt op x_currency_id; x_active + archiveerlint en de
        # embedded regels zoals in de echte Studio-view
        self.env["ir.model.fields"].create(
            {"model_id": line.id, "name": "x_bedrag",
             "field_description": "Bedrag", "ttype": "monetary",
             "state": "manual"}
        )
        self.env["ir.model.fields"].create(
            {"model_id": parent.id, "name": "x_active",
             "field_description": "Actief", "ttype": "boolean",
             "state": "manual"}
        )
        self.env["ir.model.fields"].create(
            {"model_id": parent.id, "name": "x_line_ids",
             "field_description": "Regels", "ttype": "one2many",
             "relation": line_name, "relation_field": "x_handling_id",
             "state": "manual"}
        )
        # veld op een ander model dat naar het matrix-model verwijst
        # (zoals x_studio_handling op res.partner)
        blocker = self.env["ir.model.fields"].create(
            {"model_id": self.env["ir.model"]._get("res.partner").id,
             "name": "x_d1_test_handling_ref",
             "field_description": "Handling", "ttype": "many2one",
             "relation": parent_name, "state": "manual"}
        )
        view = self.env["ir.ui.view"].create(
            {"name": "d1 test handling form", "model": parent_name,
             "type": "form",
             "arch": "<form><sheet string='Handling'>"
                     "<widget name='web_ribbon' text='Gearchiveerd'"
                     " bg_color='bg-danger' invisible='x_active == True'/>"
                     "<field name='x_active' invisible='1'/>"
                     "<field name='x_name'/>"
                     "<field name='x_studio_currency_id'/>"
                     "<field name='x_line_ids'><list>"
                     "<field name='x_bedrag'/>"
                     "<field name='x_currency_id' column_invisible='True'/>"
                     "</list></field></sheet></form>"}
        )
        self.env["ir.model.data"].create(
            {"module": "studio_customization",
             "name": "d1_test_handling_form",
             "model": "ir.ui.view", "res_id": view.id}
        )
        rec = self.env[parent_name].create(
            {"x_name": "staffel", "x_active": True}
        )
        self.env[line_name].create(
            {"x_name": "regel", "x_handling_id": rec.id}
        )

        hooks._remove_handling_models(
            self.env, model_names=(line_name, parent_name)
        )

        self.assertFalse(
            self.env["ir.model"].search(
                [("model", "in", (parent_name, line_name))]
            ),
            "modellen moeten verwijderd zijn",
        )
        self.assertFalse(view.exists(), "view moet verwijderd zijn")
        self.assertFalse(
            blocker.exists(),
            "verwijzend veld op res.partner moet mee verwijderd zijn",
        )
        # de view-deactivatie hierna mag nooit meer een validatiefout gooien
        # ('Field x_active does not exist' — go-live-rehearsal 25-09)
        hooks._deactivate_remaining_studio_views(self.env)
        for table in (parent_name, line_name):
            self.env.cr.execute(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_name = %s", (table,),
            )
            self.assertFalse(
                self.env.cr.fetchone(), "tabel %s moet verwijderd zijn" % table
            )
