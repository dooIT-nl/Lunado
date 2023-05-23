# stock.picking
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import requests, json, traceback, logging, base64
from .helper import Helper
from .shipment import Shipment
from .product import DmProduct, DmProducts
from .customer import Customer
from .deliverymatch_exception import DeliveryMatchException
from .order_handler import OrderHandler
from .shipping_option import ShippingOption, ShippingOptions
from .odoo_db import OdooDb


class StockPicking(models.Model):
    _inherit = "stock.picking"
    _logger = logging.getLogger("DeliveryMatch - Stock Picking")

    dm_shipment_id = fields.Char(string="DM Shipment ID", default=None)
    dm_carrier_name = fields.Char(string="Carrier Name")
    dm_service_level_name = fields.Char(string="Service Level Name")
    dm_service_level_description = fields.Char(string="Service Level Description")
    dm_delivery_date = fields.Char(string="Delivery Date")
    dm_pickup_date = fields.Char(string="Pickup Date")
    dm_buy_price = fields.Float(string="Buy Price")
    dm_sell_price = fields.Float(string="Sell Price")
    dm_method_id = fields.Char(string="Method ID")
    dm_check_id = fields.Char(string="Check ID")
    shipment_label_attachment = fields.Binary(string="Shipment label(s)")
    shipment_tracking_url = fields.Char(string="Tracking Link")

    dm_shipment_url = fields.Char(string="Open Shipment in DeliveryMatch")
    delivery_option_selected = fields.Boolean(default=False)
    show_hub_btn = fields.Boolean(default=False)
    dm_warehouse_number = fields.Selection(string='Warehouse nr DeliveryMatch', related='picking_type_id.dm_warehouse_number')

    @api.model
    def create(self, vals):
        res = super(StockPicking, self).create(vals)
        res.show_hub_btn = res.is_external_warehouse()
        # res.set_shipping_option()
        return res

    def write(self, values):
        result = super(StockPicking, self).write(values)
        fields = [
            "partner_id",
            "location_id",
            "move_ids_without_package",
            "company_id",
            "sale_id",
        ]
        for field in fields:
            if field == "location_id" and field in values.keys():
                self.toggle_hub_button()

            if field in values.keys():
                self.set_shipping_option()

        return result

    # @api.onchange('location_id')
    def toggle_hub_button(self):
        try:
            self.show_hub_btn = self.is_external_warehouse()

        except ValueError as e:
            self._origin.warning_popup("Error", "something went wrong...")

    def config_attribute(self, attribute, default=None):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(f"dmmodule.{attribute}", default=default)
        )

    def get_api_key(self):
        return self.config_attribute("api_key")

    def get_client_id(self):
        return self.config_attribute("client_id")

    def get_base_url(self):
        return self.config_attribute("base_url")

    def get_delivery_option_preference(self):
        return self.config_attribute("delivery_option_preference", "nothing")

    def override_product_length(self):
        return self.config_attribute("override_length")

    def get_warehouse(self):
        warehouse = self.env["stock.warehouse"].search(
            [("lot_stock_id", "=", self.location_id.id)]
        )
        return warehouse

    def get_dm_warehouse_id(self):
        warehouse = self.get_warehouse()
        return warehouse.warehouse_options
        # returns DeliveryMatch warehouse id

    def is_external_warehouse(self):
        warehouse = self.get_warehouse()
        return warehouse.dm_external_warehouse

    def show_popup(self, message):
        view_id = self._origin.env.ref("dmmodule.view_popup_wizard_form").id
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

    def get_customer_details(self) -> Customer:
        try:
            self._logger.info("fetching customer details...")
            odoo_customer = self.partner_id
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
                is_franco=is_franco

                
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

    def get_shipment_details(self, status_to_hub=False):
        if status_to_hub:
            status = "hub"
        else:
            status = "new"

        delivery_id = Helper.format_wesseling_ref(self.display_name)
        shipment = Shipment(
            delivery_id,
            self.sale_id.incoterm.code,
            self.id,
            reference=self.sale_id.client_order_ref,
            status=status,
            inbound=self.picking_type_id.dm_is_inbound
        )

        return shipment

    def has_product_in_stock(self, product_id, quantity, stock_location_id) -> bool:
        stock_product = self.env["stock.quant"].search(
            [
                ("product_id.id", "=", product_id),
                ("location_id", "=", stock_location_id),
            ]
        )

        if stock_product.available_quantity < quantity:
            return False

        if not stock_product.available_quantity:
            return False

        return True

    def get_products_details(self) -> DmProducts:
        products: DmProducts = DmProducts()
        has_x_studio_length = Helper().has_sale_order_custom_length(self.sale_id.order_line)
        is_inbound = self.picking_type_id.dm_is_inbound

        for ol in self._origin.move_ids_without_package:
            product_line = ol.product_id
            product_id = ol.product_id.id
            quantity = ol.product_uom_qty
            location_id = self.location_id.id
            in_stock: bool = self.has_product_in_stock(product_id, quantity, location_id)

            # dm_warehouse_number

            if(is_inbound== True):
                dm_warehouse_id = self.dm_warehouse_number

            if(is_inbound == False):
                warehouse = self.env["stock.warehouse"].search([("lot_stock_id.id", "=", location_id)])
                dm_warehouse_id = warehouse.warehouse_options

            length = product_line.dm_length
            if has_x_studio_length == True and self.override_product_length() == True:
                order_line = self.sale_id.order_line[0]
                if order_line.x_studio_length > 0:
                    length = order_line.x_studio_length

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
                warehouse_id=dm_warehouse_id,
                stock=in_stock,
                country_origin=product_line.dm_country_origin,
                value=product_line.list_price,
                quantity=ol.product_uom_qty,
            )

            products.add_product(product)

        return products

    def show_shipping_options(self):
        try:
            order_handler = OrderHandler(
                self.get_base_url(),
                self.get_api_key(),
                self.get_client_id(),
                self.sale_id.display_name,
            )

            shipment = self.get_shipment_details()
            customer = self.get_customer_details()
            products = self.get_products_details()

            shipping_options = order_handler.get_shipping_options(
                shipment, customer, products, True
            )
            odoo_db = OdooDb(self)
            odoo_db.delete_delivery_option(self.id)
            odoo_db.insert_into_deliver_options(shipping_options, self.id)

            new_shipment_id = shipping_options[0].shipment_id
            self.dm_shipment_url = Helper().view_shipment_url(
                self.get_base_url(), new_shipment_id
            )

            view_id = self.env.ref("dmmodule.delivery_options_tree_delivery_level").id
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
            raise UserError(e)
        except Exception as e:
            error_message = traceback.format_exc()
            self._logger.error(error_message)
            raise UserError(e)

    def set_shipping_option(self):
        try:
            shipping_preference = self.get_delivery_option_preference()

            if shipping_preference == "nothing":
                return

            order_handler = OrderHandler(
                self.get_base_url(),
                self.get_api_key(),
                self.get_client_id(),
                self.sale_id.display_name,
            )

            shipment = self.get_shipment_details()
            customer = self.get_customer_details()
            products = self.get_products_details()

            shipping_option: ShippingOption = (
                order_handler.get_shipping_option_by_preference(
                    shipment, customer, products, shipping_preference, True
                )
            )

            stockpicking = self.env["stock.picking"].search(
                [("id", "=", self._origin.id)]
            )
            stockpicking.dm_shipment_id = shipping_option.shipment_id
            stockpicking.dm_carrier_name = shipping_option.carrier_name
            stockpicking.dm_service_level_name = shipping_option.carrier_name
            stockpicking.dm_service_level_description = (
                shipping_option.service_level_description
            )
            stockpicking.dm_delivery_date = shipping_option.delivery_date
            stockpicking.dm_pickup_date = shipping_option.date_pickup

            stockpicking.dm_buy_price = shipping_option.buy_price
            stockpicking.dm_sell_price = shipping_option.sell_price

            stockpicking.dm_method_id = shipping_option.method_id
            stockpicking.dm_check_id = shipping_option.check_id
            stockpicking.dm_shipment_url = Helper().view_shipment_url(
                self.get_base_url(), shipping_option.shipment_id
            )
            stockpicking.delivery_option_selected = True

            self.message_post(subject="DeliveryMatch auto-selection", body=f"{self.get_delivery_option_preference()} shipping option selected.")
            return

        except DeliveryMatchException as e:
            self._logger.error(str(e))
            raise UserError(e)
        except Exception as e:
            error_message = traceback.format_exc()
            self._logger.error(error_message)
            raise UserError("something went wrong while selecting shipping option")

    def book_delivery(self, status_to_hub=False):
        try:
            order_handler = OrderHandler(
                self.get_base_url(),
                self.get_api_key(),
                self.get_client_id(),
                self.sale_id.display_name,
            )

            shipment = self.get_shipment_details(status_to_hub)
            customer = self.get_customer_details()
            products = self.get_products_details()

            booking_details = order_handler.book_shipment(shipment, customer, products, True)
            booked_timestamp = booking_details.get("booked_timestamp")

            sale_order = self.odoo_env.env["sale.order"].search([("id", "=", self.id)])
            sale_order.shipment_tracking_url = booking_details.get("tracking_url")
            sale_order.shipment_label_attachment = booking_details.get("shipment_label")

            if status_to_hub:
                self.message_post(
                    body=f"Order booked to HUB in DeliveryMatch on: {booked_timestamp}"
                )
                return

            self.message_post(
                body=f"Order booked to carrier in DeliveryMatch on: {booked_timestamp}"
            )

        except DeliveryMatchException as e:
            if(status_to_hub):
                raise DeliveryMatchException(e)
            else:
                return self.show_popup(str(e))

        except Exception as e:
            error_message = traceback.format_exc()
            self._logger.error(error_message)
            raise UserError(e)

    def book_delivery_to_hub(self):
        try:
            self.book_delivery(status_to_hub=True)
        except DeliveryMatchException as e:
            return self.show_popup(str(e))

        except Exception as e:
            error_message = traceback.format_exc()
            self._logger.error(error_message)
            raise UserError("An error occured while booking delivery to HUB")



    # @api.onchange('location_id', 'move_ids_without_package', 'company_id', 'sale_id')
    # def set_delivery_option(self, is_onchange=False):
    #     try:
    #         print("start")
    #         if (
    #             self.get_delivery_option_preference() != "nothing"
    #             and self._origin.id != False
    #         ):
    #             delivery_id = Helper.format_wesseling_ref(self._origin.id)
    #             sale_order_id = self._origin.sale_id.display_name
    #             operation_lines = self._origin.move_ids_without_package
    #             customer = self._origin.partner_id

    #             DmHandle = StockPickingHandler(
    #                 self.get_base_url(),
    #                 self.get_api_key(),
    #                 self.get_client_id(),
    #                 self.override_product_length(),
    #                 odoo_env=self,
    #                 shipping_preference=self.get_delivery_option_preference(),
    #             )

    #             dm_shipping_response = DmHandle.get_shipping_options_delivery_level(
    #                 sale_order_id=sale_order_id,
    #                 operation_lines=operation_lines,
    #                 sale_order=self.sale_id,
    #                 delivery_id=delivery_id,
    #                 customer=customer,
    #                 dm_shipment_id=self.dm_shipment_id,
    #             )

    #             if dm_shipping_response != True:
    #                 if is_onchange == False:
    #                     return self.warning_popup(
    #                         "DeliveryMatch - Warning", dm_shipping_response
    #                     )
    #                 else:
    #                     self._origin.message_post(
    #                         body=dm_shipping_response,
    #                         subject=_("DeliveryMatch - Warning"),
    #                         message_type="notification",
    #                     )

    #             else:
    #                 self._origin.message_post(
    #                     body=f"Selected {self._origin.get_delivery_option_preference()} delivery option!",
    #                     subject=_("DeliveryMatch - Auto selection"),
    #                 )

    #     except ValueError as e:
    #         self.warning_popup(
    #             "DeliveryMatch - Error",
    #             "Something went wrong while auto-selecting a shipping option.",
    #         )

    # def show_delivery_options(self):
    #     try:
    #         stock_picking_handler = StockPickingHandler(
    #             self.get_base_url(),
    #             self.get_api_key(),
    #             self.get_client_id(),
    #             self.override_product_length(),
    #             odoo_env=self,
    #         )
    #         delivery_id = Helper.format_wesseling_ref(self._origin.display_name)
    #         sale_order_id = self._origin.sale_id.display_name
    #         operation_lines = self._origin.move_ids_without_package
    #         customer = self._origin.partner_id
    #         stock_picking_handler.get_shipping_options_delivery_level(
    #             sale_order_id=sale_order_id,
    #             operation_lines=operation_lines,
    #             sale_order=self.sale_id,
    #             delivery_id=delivery_id,
    #             customer=customer,
    #             dm_shipment_id=self.dm_shipment_id,
    #         )

    #         # if shipping_options_response != True:
    #         #     return self.show_popup(shipping_options_response)

    #         view_id = self.env.ref("dmmodule.delivery_options_tree_delivery_level").id
    #         return {
    #             "type": "ir.actions.act_window",
    #             "name": "Shipping options",
    #             "res_model": "dm.deliver.options",
    #             "view_type": "tree",
    #             "view_mode": "tree",
    #             "view_id": view_id,
    #             "domain": [("odooOrderId", "=", self.id)],
    #             "target": "new",
    #         }
    #     except Exception as e:
    #         raise UserError(e)

    # def book_delivery(self):

    #     stock_picking_handler = StockPickingHandler(self.get_base_url(), self.get_api_key(), self.get_client_id(), self.override_product_length(), odoo_env=self)
    #     delivery_id = Helper.format_wesseling_ref(self._origin.display_name)
    #     sale_order_id = self._origin.sale_id.display_name
    #     dm_order_number = f'{sale_order_id}-{delivery_id}'

    #     operation_lines = self._origin.move_ids_without_package
    #     customer= self._origin.partner_id

    #     booking_response = stock_picking_handler.book_delivery_order(operation_lines, self.sale_id, dm_order_number, customer, self.dm_shipment_id)

    #     if booking_response != True:
    #         return self.show_popup(booking_response)

    #     self.message_post(body=f"Order booked to carrier in DeliveryMatch on: {Helper().get_time_stamp()}")
    #     return

    # def set_delivery_to_hub(self):
    #     stock_picking_handler = StockPickingHandler(self.get_base_url(), self.get_api_key(), self.get_client_id(), self.override_product_length() ,odoo_env=self)
    #     delivery_id = Helper.format_wesseling_ref(self._origin.display_name)
    #     sale_order_id = self._origin.sale_id.display_name
    #     dm_order_number = f'{sale_order_id}-{delivery_id}'

    #     operation_lines = self._origin.move_ids_without_package
    #     customer= self._origin.partner_id

    #     booking_response = stock_picking_handler.book_delivery_order(operation_lines, self.sale_id, dm_order_number, customer, self.dm_shipment_id, True)

    #     if booking_response != True:
    #         return self.show_popup(booking_response)

    #     self.message_post(body=f"Order booked to warehouse in DeliveryMatch on: {Helper().get_time_stamp()}")
    #     return
