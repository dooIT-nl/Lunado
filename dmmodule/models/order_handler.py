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

    def __init__(self, base_url, api_key, client_id):
        self.api = DmApi(base_url, api_key, client_id)
        self._logger = logging.getLogger("DeliveryMatch -- OrderHandler")

    def set_channel_franco(self, is_franco):
        if(is_franco == True):
            self.api.set_channel("FRANCO")
    
    def get_shipping_options(self, shipment: Shipment, customer: Customer, products: DmProducts):
        try:
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




