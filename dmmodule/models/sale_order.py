from odoo import api, fields, models, _, exceptions
from odoo.exceptions import UserError
import requests
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
import datetime

class SaleOrder(models.Model):
    # name="dm.sale.order"
    _logger = logging.getLogger("DeliveryMatch - SaleOrder")
    _inherit = "sale.order"
    # dm_shipment_url = "https://engine-test.deliverymatch.eu/shipment/view/"

    dm_carrierName = fields.Char(string="Carrier Name",  copy=False)
    dm_serviceLevelName = fields.Char(string="Service Level Name",  copy=False)
    dm_serviceLevelDescription = fields.Char(string="Service Level Description",  copy=False)
    dm_deliveryDate = fields.Char(string="Delivery Date",  copy=False)
    dm_pickup_date = fields.Char(string="Pickup Date",  copy=False)
    dm_buyPrice = fields.Float(string="Buy Price",  copy=False)
    dm_price = fields.Float(string="Sell Price",  copy=False)
    dm_shipment_id = fields.Char(string="DM Shipment ID", default=None,  copy=False)
    dm_methodId = fields.Char(string="Method ID",  copy=False)
    dm_checkId = fields.Char(string="Check ID",  copy=False)
    dm_shipment_booked = fields.Boolean(default=False,  copy=False)
    shipmentURL = fields.Char(copy=False)
    delivery_option_selected = fields.Boolean(default=False,  copy=False)
    order_booked = fields.Boolean(default=False,  copy=False)
    shipment_label_attachment = fields.Binary(string="Shipment label(s)",  copy=False)
    shipment_label = fields.Char(copy=False)
    shipment_tracking_url = fields.Char(copy=False)
    total_shipment_price = fields.Float(string="Total including Shipping costs", compute="_compute_custom_amount",  copy=False)
    
    show_hub_btn = fields.Boolean(default=False, copy=False)
    hide_carrier_btn = fields.Boolean(default=True, copy=False)
    
    

    @api.depends("amount_total", "amount_untaxed")
    def _compute_custom_amount(self):
        for record in self:
            record.total_shipment_price = record.amount_total + self.dm_price

    @api.onchange("warehouse_id")
    def toggle_hub_button(self):
        try:
            sale_order_to_hub = (
                self._origin.env["ir.config_parameter"]
                .sudo()
                .get_param("dmmodule.sale_order_to_hub", default=False)
            )

            if sale_order_to_hub == "True":
                self.write({"show_hub_btn": self.warehouse_id.dm_external_warehouse})
            else:
                self.write({"show_hub_btn": False})

        except ValueError as e:
            self._origin.warning_popup("Error", "something went wrong...")
            
    
    @api.model
    def create(self, vals):
        res = super(SaleOrder, self).create(vals)
        res.hide_carrier_btn = res.get_so_hide_book_carrier_btn()
        
        return res


    def write(self, values):
        result = super(SaleOrder, self).write(values)
        fields = ["partner_id", "client_order_ref", "incoterm", "warehouse_id", "order_line"]
        for field in fields:
            if field in values.keys():
                #self.message_post(body="post succes test")
                self.set_shipping_option()
                self.hide_carrier_btn = self.get_so_hide_book_carrier_btn()
        
        return result


    def config_attribute(self, attribute, default=None):
        return (
            self.env["ir.config_parameter"].sudo().get_param(f"dmmodule.{attribute}", default=default)
        )


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


    def get_so_hide_book_carrier_btn(self):
        return self.config_attribute("so_hide_book_carrier_btn")
    
    

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


    def get_shipment_details(self):
        shipment = Shipment(
            self.display_name,
            self.incoterm.code,
            self.id,
            id=self.dm_shipment_id,
            reference=self.client_order_ref
        )

        return shipment


    def get_products_details(self) -> DmProducts:
        try:
            self._logger.info("fetching products details...")
            products: DmProducts = DmProducts()
            has_x_studio_length = Helper().has_sale_order_custom_length(self.order_line)
            override_length : bool = self.override_product_length()          
            
            

            

            for ol in self.order_line:
                product_line = ol.product_template_id
                product_temp_id = ol.product_template_id.id
                quantity = ol.product_uom_qty
                dm_warehouse_id = self.warehouse_id.warehouse_options                
                location_id = self.warehouse_id.lot_stock_id.id
                in_stock: bool = self.has_product_in_stock(product_temp_id, quantity, location_id)
                length = product_line.dm_length

                
                if (has_x_studio_length == True and override_length == True):                    
                    if(ol.x_studio_length > 0):                        
                        length = ol.x_studio_length * 100
        
                if(product_line.dm_send_lot_code == True):
                    custom1= Helper.remove_letters_from_str(self.display_name)
                else:
                    custom1=None

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
                    custom1=custom1
                )

                products.add_product(product)
                
            self._logger.info("fetched products details")
            return products
        except Exception as e:
                self._logger.error("Error while fetching products details...")
                self._logger.error(traceback.format_exc())
                raise Exception(e)


    def has_product_in_stock(self, product_id, quantity, stock_location_id) -> bool:
        self._logger.info("Checking if product is in stock...")

        try:
            stock_product = self.env["stock.quant"].search(
                [
                    ("product_tmpl_id.id", "=", product_id),
                    ("location_id", "=", stock_location_id),
                ]
            )

            if stock_product.available_quantity < quantity:
                return False

            if not stock_product.available_quantity:
                return False

            return True
        except Exception as e:
            tb = traceback.format_exc()
            self._logger.error(f"{e} \n{tb}")
            raise Exception("Failed to check product availability in stock.")


    def book_sale_order(self, status_to_hub=False):
        try:
            order_handler = OrderHandler(
                self.get_base_url(),
                self.get_api_key(),
                self.get_client_id(),
                is_sale_order=True
            )

            shipment = self.get_shipment_details()
            customer = self.get_customer_details()
            products = self.get_products_details()

            booking_details = order_handler.book_shipment(shipment,customer,products)
            booked_timestamp = booking_details.get('booked_timestamp')

            sale_order = self.env["sale.order"].search([("id", "=", self.id)])
            sale_order.shipment_tracking_url = booking_details.get("tracking_url")
            sale_order.shipment_label_attachment = booking_details.get("shipment_label")

            if(status_to_hub):
                self.message_post(body=f"Order booked to HUB in DeliveryMatch on: {booked_timestamp}")
                return
            
            self.message_post(body=f"Order booked to carrier in DeliveryMatch on: {booked_timestamp}")

        except DeliveryMatchException as e:
            if(status_to_hub):
                raise DeliveryMatchException(e)
            else:
                return self.show_popup(str(e))

        except Exception as e:
            error_message = traceback.format_exc()
            self._logger.error(error_message)
            raise UserError(e)
        
    
    def book_sale_order_to_hub(self):
        try:
            self.book_sale_order(status_to_hub=True)
        except DeliveryMatchException as e:
                return self.show_popup(str(e))

        except Exception as e:
            error_message = traceback.format_exc()
            self._logger.error(error_message)
            raise UserError(e)
                    

    def show_shipping_options(self):
        try:
            order_handler = OrderHandler(
                self.get_base_url(),
                self.get_api_key(),
                self.get_client_id(),
                is_sale_order=True
            )

            shipment = self.get_shipment_details()
            customer = self.get_customer_details()
            products = self.get_products_details()

            
            shipping_options = order_handler.get_shipping_options(shipment, customer, products)
            odoo_db = OdooDb(self)
            odoo_db.delete_delivery_option(self.id)
            odoo_db.insert_into_deliver_options(shipping_options, self.id)
            
            # saleorder = self.env["sale.order"].search([("id", "=", self.id)])
            new_shipment_id = shipping_options[0].shipment_id            
            self.shipmentURL = Helper().view_shipment_url(self.get_base_url(), new_shipment_id)
            
            self.dm_shipment_id = new_shipment_id


            if(shipping_options[0].method_id == None):
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
            
            shipping_preference =  self.get_delivery_option_preference()

            if shipping_preference == "nothing":
                return

            order_handler = OrderHandler(
                self.get_base_url(),
                self.get_api_key(),
                self.get_client_id(),
                is_sale_order=True
            )

            shipment = self.get_shipment_details()
            customer = self.get_customer_details()
            products = self.get_products_details()

            
            shipping_option: ShippingOption = order_handler.get_shipping_option_by_preference(shipment,customer, products, shipping_preference)


            saleorder = self.env["sale.order"].search([("id", "=", self._origin.id)])
            saleorder.dm_shipment_id = shipping_option.shipment_id
            saleorder.dm_carrierName = shipping_option.carrier_name
            saleorder.dm_serviceLevelName = shipping_option.carrier_name
            saleorder.dm_serviceLevelDescription = shipping_option.service_level_description
            saleorder.dm_deliveryDate = shipping_option.delivery_date
            saleorder.dm_pickup_date = shipping_option.date_pickup

            saleorder.dm_buyPrice = shipping_option.buy_price
            saleorder.dm_price = shipping_option.sell_price

            saleorder.dm_methodId = shipping_option.method_id
            saleorder.dm_checkId = shipping_option.check_id
            saleorder.shipmentURL = Helper().view_shipment_url(self.get_base_url(), shipping_option.shipment_id)
            saleorder.delivery_option_selected = True
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
