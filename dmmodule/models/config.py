from odoo import models, fields

class Config(models.TransientModel):
    _inherit = "res.config.settings"

    base_url = fields.Char(string="DeliveryMatch base URL *", required=True)
    api_key = fields.Char(string="API Key *", required=True)
    client_id = fields.Char(string="Client ID *", required=True)
    override_length = fields.Boolean(string="Take product-length from order line", default=False)

    # this hides the "SEND ORDER TO WAREHOUSE" button in sale order level.
    so_hide_book_hub_btn = fields.Boolean(string="Hide 'Send order to warehouse' button", default=False)

    # this hides the "BOOK TO CARRIER" button in sale order level.
    so_hide_book_carrier_btn = fields.Boolean(string="Hide 'Book to carrier' button", default=False)

    sale_order_as_draft = fields.Boolean(string="Insert ALL SHIPMENTS with status 'DRAFT'.", default=False)

    # IF True get scheduled_date from Stock.Picking and set delivery_date in shipment
    determine_delivery_date = fields.Boolean(string="Determine delivery date", default=False)

    delivery_option_preference = fields.Selection(
        [
            ("lowest", "Lowest price"),
            ("earliest", "Earliest date"),
            (
                "most_green",
                "Greenest delivery (Only possible in accordance with Big Mile)",
            ),
            ("nothing", "No auto selection"),
        ],
        required=True,
        string="Auto select delivery option preference *",
    )

    def get_values(self):
        res = super(Config, self).get_values()
        res['override_length'] = self.env["ir.config_parameter"].sudo().get_param("dmmodule.override_length", default=False)

        res.update(
            api_key=self.env["ir.config_parameter"].sudo().get_param("dmmodule.api_key", default=None),
            delivery_option_preference=self.env["ir.config_parameter"].sudo().get_param("dmmodule.delivery_option_preference", default="lowest"),
            client_id=self.env["ir.config_parameter"].sudo().get_param("dmmodule.client_id", default=None),
            base_url=self.env["ir.config_parameter"].sudo().get_param("dmmodule.base_url", default=None),
            so_hide_book_hub_btn=self.env["ir.config_parameter"].sudo().get_param("dmmodule.so_hide_book_hub_btn", default=False),
            so_hide_book_carrier_btn=self.env["ir.config_parameter"].sudo().get_param("dmmodule.so_hide_book_carrier_btn", default=False),
            sale_order_as_draft=self.env["ir.config_parameter"].sudo().get_param("dmmodule.sale_order_as_draft", default=False),
            determine_delivery_date=self.env["ir.config_parameter"].sudo().get_param("dmmodule.determine_delivery_date", default=False),
        )
        return res

    def set_values(self):
        super(Config, self).set_values()
        self.env["ir.config_parameter"].sudo().set_param("dmmodule.api_key", self.api_key)
        self.env["ir.config_parameter"].sudo().set_param("dmmodule.delivery_option_preference", self.delivery_option_preference)
        self.env["ir.config_parameter"].sudo().set_param("dmmodule.client_id", self.client_id)
        self.env["ir.config_parameter"].sudo().set_param("dmmodule.base_url", self.base_url)
        self.env["ir.config_parameter"].sudo().set_param("dmmodule.override_length", self.override_length)
        self.env["ir.config_parameter"].sudo().set_param("dmmodule.so_hide_book_carrier_btn",self.so_hide_book_carrier_btn)
        self.env["ir.config_parameter"].sudo().set_param("dmmodule.so_hide_book_hub_btn", self.so_hide_book_hub_btn)
        self.env["ir.config_parameter"].sudo().set_param("dmmodule.sale_order_as_draft", self.sale_order_as_draft)
        self.env["ir.config_parameter"].sudo().set_param("dmmodule.determine_delivery_date", self.determine_delivery_date)
        self.update_sale_orders()

    def update_sale_orders(self):
        sale_orders = self.env["sale.order"].search([])
        
        for sale_order in sale_orders:
            sale_order.write({"hide_carrier_btn": self.so_hide_book_carrier_btn})
            sale_order.write({"hide_hub_btn": self.so_hide_book_hub_btn})

    def select_warehouses_for_hub(self):
        view_id = self.env.ref("dmmodule.view_warehouse_list").id
        return {
            "type": "ir.actions.act_window",
            "name": "Select one or more warehouses to assign as external",
            "res_model": "stock.warehouse",
            "view_type": "tree",
            "view_mode": "tree",
            "view_id": view_id,
            "domain": [],
            "target": "new",
        }
