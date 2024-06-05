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

    def set_channel_name(self, operation_type, is_franco: bool = False):
        if is_franco:
            operation_type = f'{operation_type} - FRANCO'

        self.api.set_channel(operation_type)

    def get_shipping_options(self, shipment: Shipment, customer: Customer, products: DmProducts, operation_type, packages=None, sender_name=None):
        try:
            self.set_channel_name(operation_type=operation_type, is_franco=customer.is_franco)

            self._logger.info("Fetching shipping options")
            shipping_options = self.api.request_shipping_options(customer, shipment, products, packages=packages, sender_name=sender_name)
            return shipping_options

        except DeliveryMatchException as e:
            raise DeliveryMatchException(e)

        except Exception as e:
            self._logger.error(f"An error occurred while fetching the shipping options: {e}")
            self._logger.error(traceback.format_exc())
            raise Exception("An error occurred while fetching the shipping options")

    def get_shipping_option_by_preference(self, shipment: Shipment, customer: Customer, products: DmProducts, preference, operation_type, packages=None):
        try:
            self._logger.info("Fetching shipping option by preference")
            self.set_channel_name(operation_type=operation_type, is_franco=customer.is_franco)

            shipping_options = self.api.request_shipping_options(customer, shipment, products, False, packages=packages)
            shipping_option = self.api.get_shipping_option_by_preference(shipping_options, preference)
            self.api.update_shipment_method(shipping_option.shipment_id, shipment.odoo_order_display_name,
                                            shipping_option.method_id, shipping_option.delivery_date)
            return shipping_option

        except DeliveryMatchException as e:
            raise DeliveryMatchException(e)
        except Exception as e:
            self._logger.error(f"An error occurred while fetching the shipping option by preference: {e}")
            self._logger.error(traceback.format_exc())
            raise Exception("An error occurred while fetching the shipping option by preference")

    def book_shipment(self, shipment: Shipment, customer: Customer, products: DmProducts, operation_type, is_delivery=False, packages=None, sender_name=None, custom_fields=None):
        try:
            self._logger.info("Booking shipment")
            self.set_channel_name(operation_type=operation_type, is_franco=customer.is_franco)
            booking_response: dict = self.api.reqeust_book_shipment(customer, shipment, products, packages=packages, sender_name=sender_name, custom_fields=custom_fields)
            # returns a dictionary with the following structure: tracking_url, shipment_label, booked_timestamp
            return booking_response

        except DeliveryMatchException as e:
            raise DeliveryMatchException(e)
        except Exception as e:
            self._logger.error(f"An error occurred while booking the shipment: {e}")
            self._logger.error(traceback.format_exc())
            raise Exception("An error occurred while booking the shipment")
