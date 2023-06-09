import json, logging, traceback
import requests
import base64
from .dm_api import DmApi
from .helper import Helper
from .deliverymatch_exception import DeliveryMatchException
from .customer import Customer
from .product import DmProducts
from .shipping_option import *
from .shipment import Shipment
from odoo.tools import html2plaintext


class OrderHandler:

    def __init__(self, base_url, api_key, client_id, sale_order_display_name = None):
        self.api = DmApi(base_url, api_key, client_id)
        self._logger = logging.getLogger("DeliveryMatch -- OrderHandler")
        self.sale_order_display_name = sale_order_display_name

    
    def has_sale_order_in_dm(self):
        self._logger.info("Checking if sale order exists in DeliveryMatch")
        try:        
            sale_order_num = self.sale_order_display_name
            
            if sale_order_num == "False" or sale_order_num == False:
                raise DeliveryMatchException(f"Sale order number cannot be empty")
            
            has_sale_id = self.api.has_ordernumber_in_dm(sale_order_num)
            
            if not has_sale_id:
                self._logger.error(f"Order {self.sale_order_display_name} does not exist in DeliveryMatch")
                raise DeliveryMatchException(f"Order {self.sale_order_display_name} does not exist in DeliveryMatch. In order to create a new order, you must create a sale order first in DeliveryMatch.")
            
            
            self._logger.info("Sale order exists in DeliveryMatch")
            return True

        except DeliveryMatchException as e:
            self._logger.error("Sale order does not exist in DeliveryMatch")
            raise DeliveryMatchException(e)
        
        
    def generate_delivery_number(self, sale_order_number, shipment_id):
        letters: list[str] = [chr(i) for i in range(ord('a'), ord('z')+1)]
        
        for l in letters:
            letter : str = l.upper()
            delivery_number : str = f"{sale_order_number}{letter}"
            
            order_found = self.api.has_ordernumber_in_dm(delivery_number)
            self._logger.info(f"order found with g_order_number: {delivery_number}")
            
            if shipment_id != False:
                self._logger.info(f"shipment_id: {shipment_id}")
                delivery_number = self.api.get_shipment_by_shipment_id(shipment_id)['shipment']['orderNumber']
                return delivery_number
            else:
                if(order_found == False):
                    return delivery_number

        
        
        
    def set_channel_franco(self, is_franco):
        if(is_franco == True):
            self.api.set_channel("FRANCO")


    
    def get_shipping_options(self, shipment: Shipment, customer: Customer, products: DmProducts, is_delivery = False):
        try:
            if(is_delivery):
                self.has_sale_order_in_dm()       
                shipment.odoo_order_display_name = self.generate_delivery_number(self.sale_order_display_name, shipment.id)                    
            
            self.set_channel_franco(customer.is_franco)

            self._logger.info("Fetching shipping options")
            shipping_options = self.api.request_shipping_options(customer, shipment, products)
            return shipping_options
        
        except DeliveryMatchException as e:
            raise DeliveryMatchException(e)

        except Exception as e:
            self._logger.error(f"An error occurred while fetching the shipping options: {e}")
            self._logger.error(traceback.format_exc())
            raise Exception("An error occurred while fetching the shipping options")
        
    
    def get_shipping_option_by_preference(self, shipment: Shipment, customer: Customer, products: DmProducts, preference, is_delivery= False):
        try:
            self._logger.info("Fetching shipping option by preference")
            if(is_delivery):
                self.has_sale_order_in_dm()
                shipment.odoo_order_display_name = self.generate_delivery_number(self.sale_order_display_name, shipment.id)
            
            self.set_channel_franco(customer.is_franco)

             
            shipping_options = self.api.request_shipping_options(customer, shipment, products, False)
            shipping_option = self.api.get_shipping_option_by_preference(shipping_options, preference)
            self.api.updateShipmentMethod(shipping_option.shipment_id, shipment.odoo_order_display_name, shipping_option.method_id,shipping_option.delivery_date)
            return shipping_option
        
        except DeliveryMatchException as e:
            raise DeliveryMatchException(e)
        except Exception as e:
            self._logger.error(f"An error occurred while fetching the shipping option by preference: {e}")
            self._logger.error(traceback.format_exc())
            raise Exception("An error occurred while fetching the shipping option by preference")
        

    
    def book_shipment(self, shipment:Shipment, customer: Customer, products: DmProducts, is_delivery=False):
        try:
            self._logger.info("Booking shipment")
            if(is_delivery):
                self.has_sale_order_in_dm()
                shipment.odoo_order_display_name = self.generate_delivery_number(self.sale_order_display_name, shipment.id)
            
            self.set_channel_franco(customer.is_franco)

            
            booking_response: dict = self.api.reqeust_book_shipment(customer, shipment, products)
            # returns a dictionary with the following structure: tracking_url, shipment_label, booked_timestamp
            return booking_response



        except DeliveryMatchException as e:
            raise DeliveryMatchException(e)
        except Exception as e:
            self._logger.error(f"An error occurred while booking the shipment: {e}")
            self._logger.error(traceback.format_exc())
            raise Exception("An error occurred while booking the shipment")




