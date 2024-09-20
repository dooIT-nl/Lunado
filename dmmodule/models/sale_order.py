from odoo import api, fields, models, _
from odoo.exceptions import UserError
import traceback
import logging
from .deliverymatch_exception import DeliveryMatchException
from .customer import Customer
from .product import DmProduct, DmProducts
from .helper import Helper
from .odoo_db import OdooDb
from .shipping_option import ShippingOption
from .order_handler import OrderHandler
from .shipment import Shipment
from ..helpers.list_helper import ListHelper


class SaleOrder(models.Model):
    _logger = logging.getLogger("DeliveryMatch - SaleOrder")
    _inherit = "sale.order"
    # dm_shipment_url = "https://engine-test.deliverymatch.eu/shipment/view/"

    # Inherited fields
    incoterm = fields.Many2one(required=True)

    # custom fields
    dm_carrierName = fields.Char(string="Carrier Name", copy=False)
    dm_serviceLevelName = fields.Char(string="Service Level Name", copy=False)
    dm_serviceLevelDescription = fields.Char(string="Service Level Description", copy=False)
    dm_deliveryDate = fields.Char(string="Delivery Date", copy=False)
    dm_pickup_date = fields.Char(string="Pickup Date", copy=False)
    dm_buyPrice = fields.Float(string="Buy Price", copy=False)
    dm_price = fields.Float(string="Sell Price", copy=False)
    dm_shipment_id = fields.Char(string="DM Shipment ID", default=None, copy=False)
    dm_methodId = fields.Char(string="Method ID", copy=False)
    dm_checkId = fields.Char(string="Check ID", copy=False)
    dm_shipment_booked = fields.Boolean(default=False, copy=False)
    shipmentURL = fields.Char(copy=False)
    delivery_option_selected = fields.Boolean(default=False, copy=False)
    order_booked = fields.Boolean(default=False, copy=False)
    shipment_label_attachment = fields.Binary(string="Shipment label(s)", copy=False)
    shipment_label = fields.Char(copy=False)
    shipment_tracking_url = fields.Char(copy=False)
    total_shipment_price = fields.Float(string="Total including Shipping costs", compute="_compute_custom_amount", copy=False)
    packages = fields.One2many("dm.package", "sale_order_id", string="Packages")
    show_packages = fields.Boolean(compute="_compute_show_packages", default=False)
    tracking_urls = fields.Html(string="Tracking URL's", copy=False)
    delivery_orders_iterator = fields.Integer(string="Keeps track of created deliveries", copy=False, default=0)
    dm_carrier_id = fields.Integer(string="Carrier ID", default=None, copy=False)
    service_level_id = fields.Integer(string="Service Level ID", default=None, copy=False)
    extend_carrier_to_delivery = fields.Boolean(string="Extend carrier and service level to delivery", copy=False)
    dm_config_id = fields.Integer("DM Configuration ID", copy=False, default=None)

    # TODO: temp vars for save xml removal
    hide_hub_btn = fields.Boolean(default=False, copy=False)
    hide_carrier_btn = fields.Boolean(default=True, copy=False)

    def inherit_carrier_from_sales_order(self):
        return bool(self.config_attribute("inherit_carrier_service_sales_order", default=False))

    @api.model
    def _compute_show_packages(self):
            for record in self:
                record.show_packages = self.config_attribute("calculate_packages")

    @api.depends("amount_total", "amount_untaxed")
    def _compute_custom_amount(self):
        for record in self:
            record.total_shipment_price = record.amount_total + self.dm_price

    @api.model
    def create(self, vals):
        res = super(SaleOrder, self).create(vals)
        res.extend_carrier_to_delivery = res.inherit_carrier_from_sales_order()
        return res

    def is_external_warehouse(self):
        warehouse_id = self.warehouse_id.id
        db_warehouse = self.env['stock.warehouse'].search([('id', '=', warehouse_id)], limit=1)
        return db_warehouse.dm_external_warehouse == True

    def write(self, values):
        return super(SaleOrder, self).write(values)

    def config_attribute(self, attribute, default=None):
        return (
            self.env["ir.config_parameter"].sudo().get_param(f"dmmodule.{attribute}", default=default)
        )

    def get_sales_order_lines_as_packages(self):
        if not bool(self.config_attribute("calculate_packages")):
            return []
        
        all_order_lines = self.order_line

        order_lines, combinable = ListHelper.partition(
            lambda x: x.product_template_id.dm_combinable_in_package == False, all_order_lines
        )

        if len(set(combinable)) == 1: order_lines = combinable

        packages = list(map(lambda line: line.as_deliverymatch_packages(), order_lines))

        if len(combinable) > 1:
            combined_values = {
                "weight": 0,
                "volume": 0
            }

            for product in combinable:
                combined_values["weight"] = combined_values["weight"] + (product.product_template_id.weight * product.product_uom_qty)
                combined_values["volume"] = combined_values["volume"] + (product.product_template_id.volume * product.product_uom_qty)

            packages.append(combinable[0].as_deliverymatch_packages(combined_values))

        return [i for i in ListHelper.flatten(packages) if i is not None]


    def get_api_key(self):
        return self.config_attribute("api_key")

    def get_client_id(self):
        return self.config_attribute("client_id")

    def get_base_url(self):
        return self.config_attribute("base_url")

    def get_delivery_option_preference(self):
        return self.config_attribute("delivery_option_preference")

    def override_product_length(self) -> bool:
        return bool(self.config_attribute("override_length", default=False))

    def config_sale_order_as_draft(self):
        return bool(self.config_attribute("sale_order_as_draft"))

    # MAATWERK LUNADO
    def get_is_dropshipment(self) -> bool:
        return bool(getattr(self, 'x_studio_dropshipment', False))

    def get_customer_details(self) -> Customer:
        try:
            self._logger.info("fetching customer details...")
            odoo_customer = self.partner_shipping_id
            is_franco = self.partner_id.is_franco_order

            customer: Customer = Customer(
                odoo_customer.id,
                odoo_customer.name,
                odoo_customer.parent_id.name,
                odoo_customer.street,
                odoo_customer.street2,
                odoo_customer.street,
                odoo_customer.zip,
                odoo_customer.city,
                odoo_customer.country_code,
                odoo_customer.phone,
                odoo_customer.email,
                is_company=odoo_customer.is_company,
                is_franco=is_franco,
                state=odoo_customer.state_id.code
            )
            return customer
        except DeliveryMatchException as e:
            self._logger.error("Error while fetching customer details...")
            self._logger.error(traceback.format_exc())
            raise DeliveryMatchException(e)
        except Exception as e:
            self._logger.error("Error while fetching customer details...")
            self._logger.error(traceback.format_exc())
            raise Exception(e)

    def get_shipment_details(self):
        shipment_id = self.dm_shipment_id

        if Helper.is_empty(shipment_id):
            shipment_id = False

        status: str = "new"
        if self.config_sale_order_as_draft(): status = "DRA"

        shipment = Shipment(
            odoo_order_display_name=self.display_name,
            incoterm=self.incoterm.code if self.incoterm.code else None,
            odoo_order_id=self.id,
            id=shipment_id,
            reference=self.client_order_ref,
            status=status,
            is_external_warehouse=self.is_external_warehouse()
        )

        shipment.format_shipment_reference()

        return shipment

    def get_products_details(self) -> DmProducts:
        try:
            self._logger.info("fetching products details...")
            products: DmProducts = DmProducts()
            override_length: bool = self.override_product_length()

            products_list = list(map(lambda line: line.as_deliverymatch_product(), self.order_line))

            for ol in self.order_line:
                product_line = ol.product_template_id

                if product_line.detailed_type != "product" or ol.product_uom_qty <= 0:
                    continue

                quantity = ol.product_uom_qty
                length = product_line.dm_length

                if hasattr(ol, 'x_studio_qty') and hasattr(ol, 'x_studio_length') and override_length:
                    if ol.x_studio_length > 0:
                        length = ol.x_studio_length * 100
                        quantity = ol.x_studio_qty  # Maatwerk Lunado Hoeveelheid

                custom1 = None
                if product_line.dm_send_lot_code:
                    custom1 = Helper.remove_letters_from_str(self.display_name)

                product = DmProduct(
                    content=product_line.name,
                    description=product_line.name,
                    weight=product_line.weight,
                    length=length,
                    width=product_line.dm_width,
                    height=product_line.dm_height,
                    is_fragile=product_line.dm_is_fragile,
                    is_dangerous=product_line.dm_is_dangerous,
                    sku=product_line.dm_sku,
                    hscode=product_line.dm_hscode,
                    barcode=product_line.barcode,
                    warehouse_id=self.warehouse_id.warehouse_options,  # dm_warehouse_id
                    stock=(product_line.qty_available < quantity),
                    country_origin=product_line.dm_country_origin,
                    value=product_line.list_price,
                    quantity=quantity,
                    custom1=custom1,
                    dangerous_goods={"UN": product_line.un_number, "packingType": product_line.dg_packing_instruction} if product_line.dm_is_dangerous else None,
                    lithium_battery_weight= product_line.dm_lithium_battery_weight
                )

                products.add_product(product)

            self._logger.info("fetched products details")
            return products
        except Exception as e:
            self._logger.error("Error while fetching products details...")
            self._logger.error(traceback.format_exc())
            raise Exception(e)


    def show_shipping_options(self):
        try:

            # IF SHIPMENT OPTION AUTO SELECT IS ACTIVATED
            if self.get_delivery_option_preference() != "nothing":
                self.set_shipping_option()
                return

            order_handler = OrderHandler(
                self.get_base_url(),
                self.get_api_key(),
                self.get_client_id(),
                self.get_is_dropshipment()
            )

            shipment = self.get_shipment_details()
            customer = self.get_customer_details()
            products = self.get_products_details()
            packages = self.get_sales_order_lines_as_packages()

            self._logger.info("packages=%s", packages)

            shipping_options: ShippingOption = order_handler.get_shipping_options(shipment, customer, products, operation_type='saleorder', packages=packages)

            self.packages.unlink()
            for package in packages:
                self.write({"packages": [(0, 0, {
                    "height": package['height'],
                    "length": package['length'],
                    "width": package['width'],
                    "weight": package['weight'],
                    "description": package["description"],
                    "type": package["type"],
                })]})

            odoo_db = OdooDb(self)
            odoo_db.delete_delivery_option(self.id)
            odoo_db.insert_into_deliver_options(shipping_options, self.id)

            new_shipment_id = shipping_options[0].shipment_id
            self.shipmentURL = Helper().view_shipment_url(self.get_base_url(), new_shipment_id)

            self.dm_shipment_id = new_shipment_id

            if shipping_options[0].method_id == None:
                raise DeliveryMatchException("During the selection of shipping options, it was discovered that there were no carriers currently available.")

            view_id = self.env.ref("dmmodule.delivery_options_tree").id
            return {
                "type": "ir.actions.act_window",
                "name": "Shipping options",
                "res_model": "dm.deliver.options",
                "view_type": "tree",
                "view_mode": "tree",
                "view_id": view_id,
                "domain": [("odooOrderId", "=", self.id)],
                "target": "new",
            }

        except DeliveryMatchException as e:
            return self.show_popup(e)
        except Exception as e:
            error_message = traceback.format_exc()
            self._logger.error(error_message)
            raise UserError(e)

    def set_shipping_option(self):
        try:

            order_handler = OrderHandler(
                self.get_base_url(),
                self.get_api_key(),
                self.get_client_id(),
                self.get_is_dropshipment()
            )

            shipment = self.get_shipment_details()
            customer = self.get_customer_details()
            products = self.get_products_details()
            packages = self.get_sales_order_lines_as_packages()


            shipping_option : ShippingOption= order_handler.get_shipping_option_by_preference(
                shipment=shipment,
                customer=customer,
                products=products,
                preference=self.get_delivery_option_preference(),
                operation_type="saleorder",
                packages=packages,
            )

            if bool(self.config_attribute("calculate_packages")):
                self.packages.unlink()
                for package in packages:
                    self.write({"packages": [(0, 0, {
                        "height": package['height'],
                        "length": package['length'],
                        "width": package['width'],
                        "weight": package['weight'],
                        "description": package["description"],
                        "type": package["type"],
                    })]})

            saleorder = self.env["sale.order"].search([("id", "=", self._origin.id)])
            saleorder.dm_shipment_id = shipping_option.shipment_id
            saleorder.dm_carrierName = shipping_option.carrier_name
            saleorder.dm_serviceLevelName = shipping_option.service_level_name
            saleorder.dm_serviceLevelDescription = shipping_option.service_level_description
            saleorder.dm_deliveryDate = shipping_option.delivery_date
            saleorder.dm_pickup_date = shipping_option.date_pickup

            saleorder.dm_buyPrice = shipping_option.buy_price
            saleorder.dm_price = shipping_option.sell_price

            saleorder.dm_methodId = shipping_option.method_id
            saleorder.dm_checkId = shipping_option.check_id
            saleorder.shipmentURL = Helper().view_shipment_url(self.get_base_url(), shipping_option.shipment_id)
            saleorder.delivery_option_selected = True
            saleorder.dm_config_id = shipping_option.config_id

            self.message_post(subject="DeliveryMatch auto-selection", body=f"{self.get_delivery_option_preference()} shipping option selected.")

            return

        except DeliveryMatchException as e:
            self._logger.error(str(e))
            raise UserError(e)
        except Exception as e:
            error_message = traceback.format_exc()
            self._logger.error(error_message)
            raise UserError("something went wrong while selecting shipping option")

    def show_popup(self, message):
        view_id = self.env.ref("dmmodule.view_popup_wizard_form").id
        return {
            "type": "ir.actions.act_window",
            "name": "DeliveryMatch - Warning",
            "view_mode": "form",
            "res_model": "popup_wizard",
            "views": [(view_id, "form")],
            "target": "new",
            "context": {
                "default_message": message,
            },
        }

    def warning_popup(self, title, message):
        return {"warning": {"title": title, "message": message}}
