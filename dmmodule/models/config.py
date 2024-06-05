from odoo import models, fields

class Config(models.TransientModel):
    _inherit = "res.config.settings"

    base_url = fields.Char(string="DeliveryMatch base URL *", required=True)
    api_key = fields.Char(string="API Key *", required=True)
    client_id = fields.Char(string="Client ID *", required=True)
    override_length = fields.Boolean(string="Take product-length from order line", default=False)

    sale_order_as_draft = fields.Boolean(string="Insert ALL SHIPMENTS with status 'DRAFT'.", default=False)
    # IF True get scheduled_date from Stock.Picking and set pickup date in shipment
    determine_delivery_date = fields.Boolean(string="Determine pickup date", default=False)
    calculate_packages = fields.Boolean(string="Calculate packages based on product packages", default=False)

    # INHERIT SALES ORDER CARRIER AND SERVICE_LEVEL
    inherit_carrier_service_sales_order = fields.Boolean(string="Inherit carrier selection from Sales Order", default=False)

    shipment_action_print = fields.Boolean(string="Activate action print", default=False)

    # SHOW HS-CODE IN DELIVERY -> DETAILED OPERATIONS
    show_hscode_delivery_detailed_operations = fields.Boolean(string="Show HS-CODE in detailed operations", default=False)

    #PACKAGE Description, Type, Length, Width & Height
    package_description = fields.Char(string="Package description", default="Default")
    package_type = fields.Char(string="Package type", default="Default")
    package_length = fields.Integer(string="Package length", default=10)
    package_width = fields.Integer(string="Package width", default=10)
    package_height = fields.Integer(string="Package height", default=10)

    delivery_option_preference = fields.Selection(
        [
            ("lowest", "Lowest price"),
            ("earliest", "Earliest date"),
            (
                "most_green",
                "Greenest delivery (Only possible in accordance with BigMile)",
            ),
            ("nothing", "No auto selection"),
        ],
        required=True,
        string="Auto select delivery option preference",
    )

    # BOOK ORDER VALIDATION
    book_order_validation = fields.Boolean(string="Book order validation", default=False)

    def get_values(self):
        res = super(Config, self).get_values()
        res['override_length'] = self.env["ir.config_parameter"].sudo().get_param("dmmodule.override_length", default=False)

        res.update(
            api_key=self.env["ir.config_parameter"].sudo().get_param("dmmodule.api_key", default=None),
            delivery_option_preference=self.env["ir.config_parameter"].sudo().get_param("dmmodule.delivery_option_preference", default="lowest"),
            client_id=self.env["ir.config_parameter"].sudo().get_param("dmmodule.client_id", default=None),
            base_url=self.env["ir.config_parameter"].sudo().get_param("dmmodule.base_url", default=None),
            sale_order_as_draft=self.env["ir.config_parameter"].sudo().get_param("dmmodule.sale_order_as_draft", default=False),
            determine_delivery_date=self.env["ir.config_parameter"].sudo().get_param("dmmodule.determine_delivery_date", default=False),
            calculate_packages=self.env["ir.config_parameter"].sudo().get_param("dmmodule.calculate_packages", default=False),
            inherit_carrier_service_sales_order=self.env["ir.config_parameter"].sudo().get_param("dmmodule.inherit_carrier_service_sales_order", default=False),
            shipment_action_print=self.env["ir.config_parameter"].sudo().get_param("dmmodule.shipment_action_print", default=False),
            show_hscode_delivery_detailed_operations=self.env["ir.config_parameter"].sudo().get_param("dmmodule.show_hscode_delivery_detailed_operations", default=False),
            package_description=self.env["ir.config_parameter"].sudo().get_param("dmmodule.package_description", default="Default"),
            package_type=self.env["ir.config_parameter"].sudo().get_param("dmmodule.package_type", default="Default"),
            package_length=self.env["ir.config_parameter"].sudo().get_param("dmmodule.package_length", default=10),
            package_width=self.env["ir.config_parameter"].sudo().get_param("dmmodule.package_width", default=10),
            package_height=self.env["ir.config_parameter"].sudo().get_param("dmmodule.package_height", default=10),
            book_order_validation=self.env["ir.config_parameter"].sudo().get_param("dmmodule.book_order_validation",default=False),

        )
        return res

    def set_values(self):
        super(Config, self).set_values()
        self.env["ir.config_parameter"].sudo().set_param("dmmodule.api_key", self.api_key)
        self.env["ir.config_parameter"].sudo().set_param("dmmodule.delivery_option_preference", self.delivery_option_preference)
        self.env["ir.config_parameter"].sudo().set_param("dmmodule.client_id", self.client_id)
        self.env["ir.config_parameter"].sudo().set_param("dmmodule.base_url", self.base_url)
        self.env["ir.config_parameter"].sudo().set_param("dmmodule.override_length", self.override_length)
        self.env["ir.config_parameter"].sudo().set_param("dmmodule.sale_order_as_draft", self.sale_order_as_draft)
        self.env["ir.config_parameter"].sudo().set_param("dmmodule.determine_delivery_date", self.determine_delivery_date)
        self.env["ir.config_parameter"].sudo().set_param("dmmodule.calculate_packages", self.calculate_packages)
        self.env["ir.config_parameter"].sudo().set_param("dmmodule.inherit_carrier_service_sales_order", self.inherit_carrier_service_sales_order),
        self.env["ir.config_parameter"].sudo().set_param("dmmodule.shipment_action_print", self.shipment_action_print)
        self.env["ir.config_parameter"].sudo().set_param("dmmodule.show_hscode_delivery_detailed_operations", self.show_hscode_delivery_detailed_operations)
        self.env["ir.config_parameter"].sudo().set_param("dmmodule.package_description", self.package_description)
        self.env["ir.config_parameter"].sudo().set_param("dmmodule.package_type", self.package_type)
        self.env["ir.config_parameter"].sudo().set_param("dmmodule.package_length", self.package_length)
        self.env["ir.config_parameter"].sudo().set_param("dmmodule.package_width", self.package_width)
        self.env["ir.config_parameter"].sudo().set_param("dmmodule.package_height", self.package_height)
        self.env["ir.config_parameter"].sudo().set_param("dmmodule.book_order_validation", self.book_order_validation)

        self.update_sale_orders()
        self.update_deliveries()

    def update_deliveries(self):
        stock_pickings = self.env['stock.picking'].search([])

        for stock_pick in stock_pickings:
            stock_pick.write({'show_product_hscode': self.show_hscode_delivery_detailed_operations})



    def update_sale_orders(self):
        sale_orders = self.env["sale.order"].search([])

        for sale_order in sale_orders:
            sale_order.write({"extend_carrier_to_delivery": self.inherit_carrier_service_sales_order})
            for delivery_order in sale_order.picking_ids:
                delivery_order.write({"get_carrier_from_sales_order": self.inherit_carrier_service_sales_order})



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
