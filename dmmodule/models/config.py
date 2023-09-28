from odoo import models, fields


class Config(models.TransientModel):
    _inherit = "res.config.settings"

    base_url = fields.Char(string="DeliveryMatch base URL *", required=True)
    api_key = fields.Char(string="API Key *", required=True)
    client_id = fields.Char(string="Client ID *", required=True)
    override_length = fields.Boolean(string="Enable specific length per order-item", default=False)
    
    # this hides the "SEND ORDER TO WAREHOUSE" button in sale order level.    
    sale_order_to_hub = fields.Boolean(string="Show 'Send order to warehouse' button in sale order level")

    # this hides the "BOOK TO CARRIER" button in delivery order level.
    hide_book_carrier_btn = fields.Boolean(string="Hide 'Book to carrier' button in delivery order level") 
    
    # this hides the "SEND ORDER TO WAREHOUSE" button in sale order level.
    so_hide_book_carrier_btn = fields.Boolean(string="Hide 'Book to carrier' button in sale order level") 

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
            api_key=self.env["ir.config_parameter"]
            .sudo()
            .get_param("dmmodule.api_key", default=None),
            delivery_option_preference=self.env["ir.config_parameter"]
            .sudo()
            .get_param("dmmodule.delivery_option_preference", default="lowest"),
            client_id=self.env["ir.config_parameter"]
            .sudo()
            .get_param("dmmodule.client_id", default=None),
            base_url=self.env["ir.config_parameter"]
            .sudo()
            .get_param("dmmodule.base_url", default=None),
            sale_order_to_hub=self.env["ir.config_parameter"].sudo().get_param("dmmodule.sale_order_to_hub", default=False),
            hide_book_carrier_btn=self.env["ir.config_parameter"]
            .sudo()
            .get_param("dmmodule.hide_book_carrier_btn", default=False),
            so_hide_book_carrier_btn=self.env["ir.config_parameter"]
            .sudo()
            .get_param("dmmodule.so_hide_book_carrier_btn", default=False),
        )
        return res

    def set_values(self):
        super(Config, self).set_values()
        self.env["ir.config_parameter"].sudo().set_param(
            "dmmodule.api_key", self.api_key
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "dmmodule.delivery_option_preference", self.delivery_option_preference
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "dmmodule.client_id", self.client_id
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "dmmodule.base_url", self.base_url
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "dmmodule.sale_order_to_hub", self.sale_order_to_hub
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "dmmodule.override_length", self.override_length
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "dmmodule.hide_book_carrier_btn", self.hide_book_carrier_btn
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "dmmodule.so_hide_book_carrier_btn", self.so_hide_book_carrier_btn
        )
        self.update_sale_orders()
        self.update_delivery_orders()

    def update_delivery_orders(self):
        delivery_orders = self.env["stock.picking"].search([])
        for delivery_order in delivery_orders:
            delivery_order.write({"hide_book_carrier_btn": self.hide_book_carrier_btn})


    def update_sale_orders(self):
        sale_orders = self.env["sale.order"].search([])
        
        for sale_order in sale_orders:
            sale_order.write({"hide_carrier_btn": self.so_hide_book_carrier_btn})
            
            if self.sale_order_to_hub == True:
                sale_order.write({"show_hub_btn": sale_order.warehouse_id.dm_external_warehouse})
                
            else:
                sale_order.write({"show_hub_btn": False})
                
                

    def select_warehouses_for_hub(self):
        view_id = self.env.ref("dmmodule.view_warehouse_list").id
        return {
            "type": "ir.actions.act_window",
            "name": "Select warehouses to assign as external warehouse connection in DeliveryMatch",
            "res_model": "stock.warehouse",
            "view_type": "tree",
            "view_mode": "tree",
            "view_id": view_id,
            "domain": [],
            "target": "new",
        }
