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
from ..helpers.list_helper import ListHelper


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
    dm_status = fields.Char(string="DeliveryMatch Status", copy=False)
    shipment_label_attachment = fields.Binary(string="Shipment label(s)", copy=False)
    shipment_tracking_url = fields.Char(string="Tracking Link", copy=False)

    packages = fields.One2many("dm.package", "stock_picking_id", string="Packages", ondelete='cascade')
    labels = fields.One2many("dm.label", "stock_picking_id", string="Labels", ondelete='cascade', copy=False)

    show_packages = fields.Boolean(compute="_compute_show_packages", default=False)

    dm_shipment_url = fields.Char(string="Open Shipment in DeliveryMatch", copy=False)
    delivery_option_selected = fields.Boolean(default=False, copy=False)
    dm_warehouse_number = fields.Selection(
        string="Warehouse nr DeliveryMatch",
        related="picking_type_id.dm_warehouse_number",
        copy=False
    )

    label_amount = list(map(lambda i: (f"{i}", f"{i} labels"), range(1, 11)))
    dm_label_amount = fields.Selection(
        label_amount,
        string="Select label amount",
        placeholder="Label amount",
        copy=False
    )

    dm_is_external_warehouse = fields.Boolean(default=False, copy=False)
    dm_shipment_booked = fields.Boolean(default=False, copy=False)
    tracking_urls = fields.Html(string="Tracking URL's", copy=False)
    delivery_order_number = fields.Char(string="Delivery order number", copy=False)
    get_carrier_from_sales_order = fields.Boolean(copy=False, default=False)
    dm_is_inbound = fields.Boolean(string='Inbound', related='picking_type_id.dm_is_inbound', copy=False, default=False)
    show_product_hscode = fields.Boolean(string="show HS-CODE", copy=False, default=False)

    def config_attribute(self, attribute, default=None):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(f"dmmodule.{attribute}", default=default)
        )

    @api.model
    def _compute_show_packages(self):
        for record in self:
            record.show_packages = self.config_attribute("calculate_packages")

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

    def inherit_carrier_from_sales_order(self):
        return bool(self.config_attribute("inherit_carrier_service_sales_order", default=False))

    def get_shipment_action_print(self):
        return bool(self.config_attribute("shipment_action_print", default=False))

    # retrieves from DB if warehouse is external
    def get_is_external_warehouse(self, location_id: int) -> bool:
        db_location = self.env['stock.location'].search([('id', '=', location_id)], limit=1)
        is_external_wh: bool = db_location.warehouse_id.dm_external_warehouse
        return is_external_wh

    def set_delivery_order_number(self):
        sale_order_id = Helper.remove_letters_from_str(self.origin)

        if Helper.is_empty(self.delivery_order_number):
            self.sale_id.delivery_orders_iterator += 1

        iterator = self.sale_id.delivery_orders_iterator

        if self.is_delivery() and not self.get_is_external_warehouse(self.location_id.id):
            self.delivery_order_number = f"{sale_order_id}-{iterator}"
        elif self.is_delivery() and self.get_is_external_warehouse(self.location_id.id):
            self.delivery_order_number = f"{Helper.remove_letters_from_str(self.sale_id.display_name)}"
        elif not self.is_delivery():
            self.delivery_order_number = self.get_source_document_field()

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

        res.get_carrier_from_sales_order = res.inherit_carrier_from_sales_order()
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
        self.set_delivery_order_number()

        pickup_date = ""

        # outbound
        if self.is_delivery():
            shipment_type: ShipmentType = ShipmentType.DELIVERY_ORDER
            is_external_warehouse: bool = self.get_is_external_warehouse(location_id=self.location_id.id)
            if self.get_determine_delivery_date():
                pickup_date = Helper.remove_time_from_datetime(self.scheduled_date)

        # inbound
        if not self.is_delivery():
            pickup_date = Helper.remove_time_from_datetime(self.scheduled_date)
            shipment_type: ShipmentType = ShipmentType.INBOUND_ORDER
            is_external_warehouse: bool = self.get_is_external_warehouse(location_id=self.location_dest_id.id)

        shipment = Shipment(
            odoo_order_display_name=self.delivery_order_number,
            incoterm=self.sale_id.incoterm.code if self.sale_id.incoterm.code else None,
            type=shipment_type,
            odoo_order_id=self.id,
            id=self.dm_shipment_id,
            reference=self.sale_id.client_order_ref,
            inbound=self.picking_type_id.dm_is_inbound,
            is_external_warehouse=is_external_warehouse,
            pickup_date=pickup_date
        )

        if(self.get_shipment_action_print()):
            shipment.action = 'print'

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
                    dangerous_goods={"UN": product_line.un_number, "packingType": product_line.dg_packing_instruction}
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

    def get_sales_order_lines_as_packages(self):
        if not bool(self.config_attribute("calculate_packages")):

            if Helper.is_empty(self.dm_label_amount): return []

            all_move_ids_without_package = self._origin.move_ids_without_package
            total_weight = sum(line.product_tmpl_id.weight * line.product_uom_qty for line in  all_move_ids_without_package)
            total_packages = int(self.dm_label_amount)
            package_weight = total_weight / total_packages
            package_description = self.config_attribute("package_description")
            package_type = self.config_attribute("package_type")
            package_length = self.config_attribute("package_length")
            package_width = self.config_attribute("package_width")
            package_height = self.config_attribute("package_height")
            packages = list(map(lambda p: {"description": package_description, "type": package_type, "height": package_height, "width": package_width, "length": package_length, "weight": package_weight}, range(total_packages)))

            return packages

        all_move_ids = self.move_ids
        move_ids, combinable = ListHelper.partition(
            lambda x: x.product_tmpl_id.dm_combinable_in_package == False, all_move_ids)

        packages = list(map(lambda m: m.as_deliverymatch_packages(), move_ids))

        if len(combinable) > 0:
            combined_values = {
                "weight": 0,
                "volume": 0
            }

            for product in combinable:
                combined_values["weight"] = combined_values["weight"] + (product.product_tmpl_id.weight * product.product_uom_qty)
                combined_values["volume"] = combined_values["volume"] + (product.product_id.volume * product.product_uom_qty)

            packages.append(combinable[0].as_deliverymatch_packages(combined_values))

        return [i for i in ListHelper.flatten(packages) if i is not None]

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
            packages = self.get_sales_order_lines_as_packages()

            shipping_options = order_handler.get_shipping_options(shipment, customer, products, packages=packages)

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
            packages = self.get_sales_order_lines_as_packages()

            shipping_option: ShippingOption = (
                order_handler.get_shipping_option_by_preference(
                    shipment, customer, products, shipping_preference, self.is_delivery(), packages=packages
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

            packages = list(map(lambda p: p.to_api_format(), self.packages)) if bool(self.config_attribute('calculate_packages')) else self.get_sales_order_lines_as_packages()
            booking_details = order_handler.book_shipment(
                shipment, customer, products, self.is_delivery(),
                packages=packages
            )

            for index, label in enumerate(booking_details.get("packages")):
                try:
                    self.write({"labels": [(0, 0, {
                        "label_url": label["labelURL"],
                        "barcode": label["barcode"],
                        "tracking_url": label["trackingURL"] if "trackingURL" in label else "",
                        "weight": self.packages[index].weight,
                        "length": self.packages[index].length,
                        "height": self.packages[index].height,
                        "width": self.packages[index].width,
                        "type": self.packages[index].type,
                        "description": self.packages[index].description,
                    })]})
                except IndexError:
                    self.write({"labels": [(0, 0, {
                        "label_url": label["labelURL"],
                        "barcode": label["barcode"],
                        "tracking_url": label["trackingURL"] if "trackingURL" in label else "",
                    })]})

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

    def set_carrier_from_sale_order(self):
        order_handler = OrderHandler(
            self.get_base_url(),
            self.get_api_key(),
            self.get_client_id()
        )

        shipment = self.get_shipment_details()
        customer = self.get_customer_details()
        products = self.get_products_details()
        packages = self.get_sales_order_lines_as_packages()
        get_shipment_response = order_handler.api.get_shipment(id=shipment.id)

        request_url = order_handler.api.set_request_url(shipment_id=shipment.id,
                                                        get_shipment_response=get_shipment_response)
        if Helper.is_empty(shipment.id) is not True:
            order_handler.api.is_shipment_booked(id=shipment.id, shipment=get_shipment_response, throw_on_booked=True)

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

        body = {
            "client": {
                "id": self.get_client_id(),
                "channel": order_handler.set_channel_name(shipment.type, customer.is_franco),
                "action": "select",
            },
            "shipment": {
                "id": shipment.id,
                "status": shipment.status,
                "orderNumber": shipment.odoo_order_display_name,
                "reference": shipment.reference,
                "language": shipment.language,
                "currency": shipment.currency,
                "inbound": shipment.inbound,
                "incoterm": shipment.incoterm,
                "note": customer.note,
                'carrier': self.sale_id.dm_carrier_id,
                'service': self.sale_id.service_level_id
            },
            "customer": {
                "id": customer.id,
                "address": {
                    "name": customer.name,
                    "companyName": customer.company_name,
                    "address1": customer.address1,
                    "street": customer.street,
                    "postcode": customer.postcode,
                    "city": customer.city,
                    "country": customer.country,
                },
                "contact": {
                    "phoneNumber": customer.phone_number,
                    "email": customer.email,
                },
            },
            "quote": {"product": products.get_api_format()},
            "fragileGoods": products.has_fragile_products(),
            "dangerousGoods": products.has_dangerous_products(),
            "priceIncl": products.total_price_incuding_vat(),
            "weight": products.total_weight(),
        }

        if packages:
            body.update({"packages": {"package": packages}})

        if not Helper.is_empty(shipment.pickup_date):
            body['shipment']["firstPickupDate"] = shipment.pickup_date

        response = order_handler.api.api_request(
            data=body,
            url=request_url,
            method="POST",
            return_raw=True
        )

        if response.status_code != 200:
            self.show_popup({response.text})
            return

        shipment_id = json.loads(response.text).get('shipmentID')

        if self.config_attribute('determine_delivery_date', False):
            order_handler.api.save_pickup_date(shipment_id, Helper.remove_time_from_datetime(self.scheduled_date))

        getNewShipment = order_handler.api.get_shipment(shipment_id)

        self.dm_service_level_name = getNewShipment.get('serviceLevel').get('name')
        self.dm_service_level_description = getNewShipment.get('serviceLevel').get('description')
        self.dm_delivery_date = getNewShipment.get('shipmentMethod').get('dateDelivery')
        self.dm_pickup_date = getNewShipment.get('shipmentMethod').get('datePickup')
        self.dm_buy_price = getNewShipment.get('shipmentMethod').get('buy_price')
        self.dm_sell_price = getNewShipment.get('shipmentMethod').get('sell_price')
        self.dm_shipment_id = shipment_id
        self.delivery_option_selected = True
        self.dm_shipment_url = Helper().view_shipment_url(self.get_base_url(), shipment_id)
