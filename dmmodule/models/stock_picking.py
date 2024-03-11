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
from .shipment_type import ShipmentType


class StockPicking(models.Model):
    _inherit = "stock.picking"
    _logger = logging.getLogger("DeliveryMatch - Stock Picking")

    dm_shipment_id = fields.Char(string="DM Shipment ID", default=None, copy=False)
    dm_carrier_name = fields.Char(string="Carrier Name", copy=False)
    dm_service_level_name = fields.Char(string="Service Level Name", copy=False)
    dm_service_level_description = fields.Char(string="Service Level Description", copy=False)
    dm_delivery_date = fields.Char(string="Delivery Date", copy=False)
    dm_pickup_date = fields.Char(string="Pickup Date", copy=False)
    dm_buy_price = fields.Float(string="Buy Price", copy=False)
    dm_sell_price = fields.Float(string="Sell Price", copy=False)
    dm_method_id = fields.Char(string="Method ID", copy=False)
    dm_check_id = fields.Char(string="Check ID", copy=False)
    shipment_label_attachment = fields.Binary(string="Shipment label(s)", copy=False)
    shipment_tracking_url = fields.Char(string="Tracking Link", copy=False)

    dm_shipment_url = fields.Char(string="Open Shipment in DeliveryMatch", copy=False)
    delivery_option_selected = fields.Boolean(default=False, copy=False)
    dm_warehouse_number = fields.Selection(
        string="Warehouse nr DeliveryMatch",
        related="picking_type_id.dm_warehouse_number",
        copy=False
    )

    dm_is_external_warehouse = fields.Boolean(default=False, copy=False)
    dm_shipment_booked = fields.Boolean(default=False, copy=False)
    tracking_urls = fields.Html(string="Tracking URL's", copy=False)
    delivery_order_number = fields.Char(string="Delivery order number", copy=False)

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
        return bool(self.config_attribute("override_length", default=False))

    def get_determine_delivery_date(self):
        return bool(self.config_attribute("determine_delivery_date", default=False))

    # retrieves from DB if warehouse is external
    def get_is_external_warehouse(self, location_id: int) -> bool:
        db_location = self.env['stock.location'].search([('id', '=', location_id)], limit=1)
        is_external_wh: bool = db_location.warehouse_id.dm_external_warehouse
        return is_external_wh

    def set_delivery_order_number(self):
        sale_order_id = Helper.remove_letters_from_str(self.origin)

        # TODO: INBOUND ORDER - ON CREATE AND UPDATE

        if self.is_delivery():
            self.sale_id.delivery_orders_iterator += 1
            self.delivery_order_number = f"{sale_order_id}-{self.sale_id.delivery_orders_iterator}"

    @api.model
    def create(self, vals):
        res = super(StockPicking, self).create(vals)

        if 'location_id' not in vals and self.is_delivery():
            vals['location_id'] = self.location_id

        if 'location_dest_id' not in vals and self.is_delivery() == False:
            vals['location_dest_id'] = self.location_dest_id

        for k, v in vals.copy().items():
            if (k == 'location_id' or k == 'location_dest_id'):
                res.dm_is_external_warehouse = res.get_is_external_warehouse(v)

        return res

    def write(self, values):
        # set order to 'SEND ORDER TO WAREHOUSE' on location_id and location_dest_id
        # FOR INBOUND AND OUTBOUND ORDERS

        if 'location_id' not in values and self.is_delivery():
            values['location_id'] = self.location_id.id

        if 'location_dest_id' not in values and self.is_delivery() == False:
            values['location_dest_id'] = self.location_dest_id.id

        for k, v in values.copy().items():
            if (k == 'location_id' or k == 'location_dest_id'):
                values['dm_is_external_warehouse'] = self.get_is_external_warehouse(v)

        # TODO self.set_shipping_option()

        return super(StockPicking, self).write(values)

    def get_warehouse(self):
        is_inbound: bool = bool(self.picking_type_id.dm_is_inbound)

        lot_stock_id = self.location_id.id

        if is_inbound:
            lot_stock_id = self.location_dest_id.id

        warehouse = self.env["stock.warehouse"].search([("lot_stock_id", "=", lot_stock_id)])

        return warehouse

    def get_dm_warehouse_id(self):
        warehouse = self.get_warehouse()
        return warehouse.warehouse_options
        # returns DeliveryMatch warehouse id

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

    def is_delivery(self) -> bool:
        is_inbound: bool = self.picking_type_id.dm_is_inbound

        if is_inbound is True:
            return False

        return True

    def get_purchase_order(self, attribute, search_value):
        purchase_order = self.env["purchase.order"].search([(attribute, "=", search_value)], limit=1)
        return purchase_order

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
                is_franco=is_franco,
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

    def get_source_document_field(self):
        if (self.origin == None or self.origin == False):
            raise DeliveryMatchException(
                "In order to add an inbound order in DeliveryMatch please provide an unique number in the source document field.")

        return self.origin

    def get_shipment_details(self):
        delivery_date = ""

        # outbound
        if self.is_delivery():
            shipment_type: ShipmentType = ShipmentType.DELIVERY_ORDER
            is_external_warehouse: bool = self.get_is_external_warehouse(location_id=self.location_id.id)
            delivery_id = self.delivery_order_number
            if self.get_determine_delivery_date():
                delivery_date = Helper.remove_time_from_datetime(self.scheduled_date)

            if is_external_warehouse:
                delivery_id = Helper.remove_letters_from_str(self.sale_id.display_name)

        # inbound
        if not self.is_delivery():
            delivery_id = self.get_source_document_field()
            delivery_date = Helper.remove_time_from_datetime(self.scheduled_date)
            shipment_type: ShipmentType = ShipmentType.INBOUND_ORDER
            is_external_warehouse: bool = self.get_is_external_warehouse(location_id=self.location_dest_id.id)

        shipment = Shipment(
            odoo_order_display_name=delivery_id,
            incoterm=self.sale_id.incoterm.code,
            type=shipment_type,
            odoo_order_id=self.id,
            id=self.dm_shipment_id,
            reference=self.sale_id.client_order_ref,
            inbound=self.picking_type_id.dm_is_inbound,
            delivery_date=delivery_date,
            is_external_warehouse=is_external_warehouse
        )

        shipment.format_shipment_reference()

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
        try:
            is_inbound: bool = self.picking_type_id.dm_is_inbound
            override_length: bool = self.override_product_length()
            products: DmProducts = DmProducts()
            custom1 = ""

            for ol in self._origin.move_ids_without_package:
                product_line = ol.product_id
                quantity = ol.product_uom_qty
                length = product_line.dm_length
                dm_warehouse_id = self.get_warehouse().warehouse_options  # dm_warehouse_number

                if (hasattr(ol, 'x_studio_hoeveelheid') == True and hasattr(ol,
                                                                            'x_studio_lengte') == True and override_length == True):
                    if (ol.x_studio_lengte > 0):
                        length = ol.x_studio_lengte * 100
                        quantity = ol.x_studio_hoeveelheid  # Maatwerk Lunado Hoeveelheid

                if (product_line.detailed_type != "product" or ol.product_uom_qty <= 0): continue

                in_stock: bool = (ol.product_qty < quantity)

                if product_line.dm_send_lot_code == True and is_inbound == False:
                    custom1 = Helper.remove_letters_from_str(self.sale_id.display_name)

                if (product_line.dm_send_lot_code == True and is_inbound == True):
                    if self.origin != "False" or self.origin != False:
                        purchase_order = self.get_purchase_order("name", self.origin)
                        custom1 = Helper.remove_letters_from_str(purchase_order.origin)

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
                    quantity=quantity,
                    custom1=custom1,
                )

                products.add_product(product)

            return products

        except DeliveryMatchException as e:
            self._logger.error(f"{traceback.format_exc()}")
            raise DeliveryMatchException(e)

        except Exception as e:
            self._logger.error(f"{traceback.format_exc()}")
            self._logger.error(f"get_products_details ERROR: {e}")
            raise Exception("Error occured while fetching product details")

    def set_order_number(self):
        if self.is_delivery() == True:
            return self.sale_id.display_name

        if (self.is_delivery() == False):
            return self.get_source_document_field()

    def show_shipping_options(self):
        try:

            order_handler = OrderHandler(
                self.get_base_url(),
                self.get_api_key(),
                self.get_client_id()
            )

            shipment = self.get_shipment_details()
            customer = self.get_customer_details()
            products = self.get_products_details()
            shipping_options = order_handler.get_shipping_options(shipment, customer, products)

            odoo_db = OdooDb(self)
            odoo_db.delete_delivery_option(self.id)
            odoo_db.insert_into_deliver_options(shipping_options, self.id)

            new_shipment_id = shipping_options[0].shipment_id

            self.dm_shipment_url = Helper().view_shipment_url(self.get_base_url(), new_shipment_id)
            self.dm_shipment_id = new_shipment_id

            if (shipping_options[0].method_id == None):
                raise DeliveryMatchException(
                    "During the selection of shipping options, it was discovered that there were no carriers currently available.")

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
            return self.show_popup(e)
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
                self.get_client_id()
            )

            shipment = self.get_shipment_details()
            customer = self.get_customer_details()
            products = self.get_products_details()

            shipping_option: ShippingOption = (
                order_handler.get_shipping_option_by_preference(
                    shipment, customer, products, shipping_preference, self.is_delivery()
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

            self.message_post(
                subject="DeliveryMatch auto-selection",
                body=f"{self.get_delivery_option_preference()} shipping option selected.",
            )
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
                self.get_client_id()
            )

            shipment = self.get_shipment_details()
            if (status_to_hub): shipment.to_hub = status_to_hub

            customer = self.get_customer_details()
            products = self.get_products_details()

            booking_details = order_handler.book_shipment(
                shipment, customer, products, self.is_delivery()
            )
            booked_timestamp = booking_details.get("booked_timestamp")

            stock_picking_order = self.env["stock.picking"].search([("id", "=", self.id)])
            stock_picking_order.tracking_urls = booking_details.get("tracking_url")
            stock_picking_order.shipment_label_attachment = booking_details.get("shipment_label")

            if status_to_hub:
                self.message_post(
                    body=f"Order booked to HUB in DeliveryMatch on: {booked_timestamp}"
                )
            else:

                self.message_post(
                    body=f"Order booked to carrier in DeliveryMatch on: {booked_timestamp}"
                )
            self.dm_shipment_booked = True

        except DeliveryMatchException as e:
            if status_to_hub:
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
            # raise UserError("An error occured while booking delivery to HUB")
            raise UserError("An error occured while booking delivery to HUB")
