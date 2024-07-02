import json, logging
from datetime import datetime
import base64
import requests
import re


class DeliveryMatchException(Exception):
    pass


class Helper:
    def __init__(self):
        self._logger = logging.getLogger("DeliveryMatch - Helper")
        
        
    def contains_letters(string):
        return bool(re.search('[a-zA-Z]', string))

    def get_time_stamp(self) -> str:
        current_time = datetime.now()
        # Format the current time as yy-mm-dd h:m:s
        formatted_time = current_time.strftime("%y-%m-%d %H:%M:%S")
        return formatted_time

    def has_sale_order_custom_length(self, order_line):
        for line in order_line:
            if hasattr(line, "x_studio_length"):
                return True

            return False

    def validate_required_fields(self, fields: dict, message: str):
        for key, field in fields.items():
            if not field:
                return f"{key} {message}"

        return True

    def convert_label(self, label):
        try:
            self._logger.info("Converting label...")
            converted_label = base64.b64encode(requests.get(label).content).decode()            
            self._logger.info("Label conversion successful")
            return converted_label
        except (requests.RequestException, ValueError) as e:
            self._logger.error("Error converting label: %s", str(e))
            raise DeliveryMatchException("Error converting label: {}".format(str(e)))

    def get_external_warehouse_id(self, odoo_env, search_id):
        warehouse = odoo_env.env["stock.warehouse"].search(
            [("lot_stock_id.id", "=", search_id)]
        )
        if warehouse.dm_external_warehouse:
            return warehouse.warehouse_options
        else:
            return None

    def order_total_price(self, lines, is_product_template=False):
        self._logger.info("calculating order total price...")
        total_price = 0
        for line in lines:
            product = line.product_id

            if is_product_template:
                product = line.product_template_id

            quantity = line.product_uom_qty
            price = product.list_price * quantity
            total_price += price

        return total_price

    def has_fragile_products(self, lines, is_product_template=False) -> bool:
        for line in lines:
            product = line.product_id

            if is_product_template:
                product = line.product_template_id

            if product.dm_is_fragile:
                return True

        return False

    def has_dangerous_products(self, lines, is_product_template=False) -> bool:
        for line in lines:
            product = line.product_id

            if is_product_template:
                product = line.product_template_id

            if product.dm_is_dangerous:
                return True

        return False

    def format_shipping_options(self, data, odoo_order_id):
        shipping_options = []
        shipment_id = data["shipmentID"]
        shipment_methods: dict = data["shipmentMethods"]["all"]

        for key in shipment_methods:
            shipment_method: dict = shipment_methods.get(key)

            for method in shipment_method:
                method_id = method.get("methodID")
                check_id = method.get("checkID")
                carrier_name = method.get("carrier").get("name")
                service_level_name = method.get("serviceLevel").get("name")
                service_level_description = method.get("serviceLevel").get(
                    "description"
                )
                delivery_date = method.get("dateDelivery")
                date_pickup = method.get("datePickup")

                buy_price = method.get("buy_price")
                price = method.get("price")

                shipping_option = {
                    "carrier_name": carrier_name,
                    "service_level_name": service_level_name,
                    "service_level_description": service_level_description,
                    "delivery_date": delivery_date,
                    "date_pickup": date_pickup,
                    "buy_price": buy_price,
                    "price": price,
                    "shipment_id": shipment_id,
                    "odoo_order_id": odoo_order_id,
                    "method_id": method_id,
                    "check_id": check_id,
                }

                shipping_options.append(shipping_option)

        return tuple(shipping_options)

    def format_dm_url(self, raw_url: str):
        url_arr = raw_url.split("//")[-1].split("/")
        base_url = url_arr[0].replace("api.", "")
        return "https://" + base_url

    def view_shipment_url(self, url, shipment_id) -> str:
        url = self.format_dm_url(url)
        return f"{url}/shipment/view/{shipment_id}"

    def format_wesseling_ref(wsl_ref: str) -> str:
        if "/" in wsl_ref:
            return wsl_ref.replace("/", "")
        else:
            return wsl_ref

    def remove_letters_from_str(line):
        try:
            if not line:
                return ""
            
            result = ""
            for char in line:
                if char.isdigit():
                    result += char
            return result
        except Exception as e:
            return ""

    def remove_time_from_datetime(date_time_object):
        # Format the datetime object without the time
        date_string = date_time_object.strftime('%Y-%m-%d')
        return date_string

    @staticmethod
    def is_empty(value) -> bool:
        return value is None or value == "" or value == False or value == 0 or value == "0" or value == "False"