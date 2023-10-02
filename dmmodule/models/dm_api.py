import traceback
import requests, json, logging
from .deliverymatch_exception import DeliveryMatchException
from .customer import Customer
from .product import DmProducts
from .shipment import Shipment
from .shipping_option import ShippingOption, ShippingOptions
from .helper import Helper

class DmApi:
    def __init__(self, base_url, api_key, client_id):
        self.base_url = base_url
        self.client_id = client_id
        self.api_key = api_key
        self.headers = {
            "apikey": api_key,
            "client": str(client_id),
            "Content-Type": "application/json",
        }
        self.channel = "Odoo testing"
        self._logger = logging.getLogger("DeliveryMatch - API")
        self.check_credentials()

    
    def set_channel(self, channel):
        self.channel = channel

    def api_request(
        self, data: dict, url, method="GET", headers=None, params=None, return_raw=False
    ):
        try:
            if not headers:
                headers = self.headers

            body = json.dumps(data)

            response = requests.request(method=method, url=url, headers=headers, data=body)

            if return_raw == True:
                return response.text

            self._logger.info(f"Request URL: {str(url)}")
            self._logger.info(f"Request Body: {str(body)}")
            self._logger.info(f"response:{str(response.text)}")
            return json.loads(response.text)
        
        except json.JSONDecodeError as e:
            self._logger.error("The API response is not JSON. JSONDecodeError:", e)
            self._logger.error(f"DeliveryMatch API response: {str(response.text)}")

            raise DeliveryMatchException(f"Invalid API response from DeliveryMatch server: {str(response.text)}")
        except Exception as e:
            self._logger.error(e)
            self._logger.error(traceback.format_exc())
            self._logger.info(f"DeliveryMatch API response: {response.text}")
            raise Exception("something went wrong in api request")
        


    def reqeust_book_shipment(self, customer: Customer, shipment: Shipment, products: DmProducts):
        try:
            self._logger.info("Posting book shipment")
            odoo_order_number = shipment.odoo_order_display_name
            request_url = f"{self.base_url}/insertShipment"
            shipment_id = shipment.id

            if self.shipment_booked_by_ordernumber(odoo_order_number) == True:
                raise DeliveryMatchException(f"This shipment ({odoo_order_number}) has already been booked.")

            if shipment_id != False:
                response_shipment_id = self.get_shipment_by_shipment_id(shipment_id, True)
                if(shipment_id == response_shipment_id):
                    request_url = f"{self.base_url}/updateShipment"
                    
            if(self.has_ordernumber_in_dm(odoo_order_number) == True):
                request_url = f"{self.base_url}/updateShipment"

            body = {
                    "client": {
                        "id": self.client_id,
                        "channel": self.channel,
                        "action": "book",
                    },
                    "shipment": {
                        "id": shipment_id,
                        "status": shipment.status,
                        "orderNumber": odoo_order_number,
                        "reference": shipment.reference,
                        "language": shipment.language,
                        "currency": shipment.currency,
                        "inbound": shipment.inbound,
                        "incoterm": shipment.incoterm,
                        "note": customer.note,
                    },
                    "customer": {
                        "id": customer.id,
                        "address": {
                            "name": customer.name,
                            "companyName": customer.company_name,
                            "address1": customer.address1,
                            "address2": customer.address2,
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
                    "priceExcl": "",
                    "weight": products.total_weight(),
                }

            response = self.api_request(data=body, method="POST", url=request_url)
            self.validate_booking_response(response, shipment.to_hub)
            return self.format_booking_response(response)
        
        except DeliveryMatchException as e:
            raise DeliveryMatchException(e)
        except Exception as e:
            self._logger.error(e)
            self._logger.error(traceback.format_exc())
            raise Exception("Something went wrong while trying to book the shipment")

   
    def request_shipping_options(self, customer: Customer, shipment: Shipment, products: DmProducts, format_shipping_options=True):
        try:

            odoo_order_number = shipment.odoo_order_display_name
            request_url = f"{self.base_url}/insertShipment"
            shipment_id = shipment.id

            if self.shipment_booked_by_ordernumber(odoo_order_number) == True:
                raise DeliveryMatchException(f"This shipment ({odoo_order_number}) has already been booked.")

            if shipment_id != False:
                response_shipment_id = self.get_shipment_by_shipment_id(shipment_id, True)
                if(str(shipment_id) == str(response_shipment_id)):
                    request_url = f"{self.base_url}/updateShipment"
                    
            
            if(self.has_ordernumber_in_dm(odoo_order_number) == True):
                request_url = f"{self.base_url}/updateShipment"

            
            body_shipment = {
                    "id": shipment_id,
                    "status": "new",
                    "orderNumber": odoo_order_number,
                    "reference": shipment.reference,
                    "language": shipment.language,
                    "currency": shipment.currency,
                    "inbound": shipment.inbound,
                    "incoterm": shipment.incoterm,
                    "note": customer.note,                    
            }
            
            if(shipment.delivery_date != ""): body_shipment['deliveryDate'] = shipment.delivery_date
            
            body = {
                "client": {
                    "id": self.client_id,
                    "channel": self.channel,
                    "action": "show",
                },
                "shipment": body_shipment,
                "customer": {
                    "id": customer.id,
                    "address": {
                        "name": customer.name,
                        "companyName": customer.company_name,
                        "address1": customer.address1,
                        "address2": customer.address2,
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
                "priceExcl": "",
                "weight": products.total_weight(),
            }

            response = self.api_request(data=body, method="POST", url=request_url)
            self.validate_shipment_options_response(response)

            if(format_shipping_options):
                return self.format_shipping_options(response)
            
            return response

        except DeliveryMatchException as e:
            self._logger.error(e)
            raise DeliveryMatchException(e)
        except Exception as e:
            self._logger.error(e)
            self._logger.error(traceback.format_exc())
            raise Exception("Something went wrong while requesting shipping options from DeliveryMatch")
    
    
    def format_shipping_options(self, response):
        shipment_id = response["shipmentID"]
        shipment_methods: dict = response["shipmentMethods"]["all"]
        
        shipping_options: ShippingOptions = ShippingOptions()
        
        if "all" not in response["shipmentMethods"] or len(response["shipmentMethods"]["all"]) == 0:
            empty_shipping_option : ShippingOption = ShippingOption(shipment_id, None, None, None, None, None, None, None, None, None)
            
            shipping_options.add_shipping_option(empty_shipping_option)
            return shipping_options.get_shipping_options()

        for key in shipment_methods:
            shipment_method: dict = shipment_methods.get(key)
            
            for method in shipment_method:
                delivery_date : str =  method.get("dateDelivery")
                if not delivery_date:
                    delivery_date = ""
                
                shipping_option = ShippingOption(
                    shipment_id=shipment_id,
                    method_id=method.get("methodID"),
                    check_id=method.get("checkID"),
                    carrier_name=method.get("carrier").get("name"),
                    service_level_name=method.get("serviceLevel").get("name"),
                    service_level_description=method.get("serviceLevel").get("description"),
                    delivery_date=delivery_date,
                    date_pickup=method.get("datePickup"),
                    buy_price=method.get("buy_price"),
                    sell_price=method.get("price")
                )
                
                shipping_options.add_shipping_option(shipping_option)
        
        return shipping_options.get_shipping_options()


    def format_booking_response(self, response) -> dict:
        try:
            tracking_urls = []
            shipment_label = None
            
            if('packages' in response):
                for package in response['packages']:
                    if 'trackingURL' in package and 'barcode' in package:
                        response_tracking_url = package['trackingURL']
                        response_barcode = package['barcode']
                        tracking_urls.append(f'<a href="{response_tracking_url}">Tracking {response_barcode}</a>')
            
            if('delivery' in response and len(tracking_urls) == 0):
                if('trackingURL' in response["delivery"]):
                    response_tracking_url = response["delivery"]["trackingURL"]
                    response_barcode = response["delivery"]["barcode"]
                    tracking_urls.append(f'<a href="{response_tracking_url}">{response_barcode}</a>')
                    
            if('CMR' in response):
                if response['CMR'] != "":
                    shipment_label = Helper().convert_label(response["CMR"])
                
            if('labelURL' in response):
                if response['labelURL'] != "":
                    shipment_label = Helper().convert_label(response["labelURL"])

            booked_timestamp = Helper().get_time_stamp()

            if(len(tracking_urls) == 0):
                tracking_url = "Tracking URL unavailable."
            else:
                tracking_url = '<br>'.join(tracking_urls)

            return {
                "tracking_url": tracking_url,
                "shipment_label": shipment_label,
                "booked_timestamp": booked_timestamp
            }

        except Exception as e:
            self._logger.error(e)
            self._logger.error(traceback.format_exc())
            raise Exception("An error occurred while retrieving the tracking URL and label from DeliveryMatch")


    def get_shipping_option_by_preference(self, response, preference: str) -> ShippingOption:
        try:
        
            if preference == "lowest":
                delivery_preference = "lowestPrice"
            elif preference == "earliest":
                delivery_preference = "earliest"
            elif preference == "most_green":
                delivery_preference = "greenest"

            if(delivery_preference not in response["shipmentMethods"] and preference == "most_green"):
                raise DeliveryMatchException("To ensure that you receive the most environmentally-friendly delivery option, please specify this preference with Big Mile. In this case, please select another shipping preference.")

            if(delivery_preference not in response["shipmentMethods"]):
                raise DeliveryMatchException(f"No shipping option found for preference {preference}")

            shipment_id = response["shipmentID"]
            shipment_method: dict = response["shipmentMethods"][delivery_preference]

            if "carrier" not in shipment_method:
                raise DeliveryMatchException(f"During the selection of a shipping option, it was discovered that there were no carriers currently available.")
            
            delivery_date = shipment_method.get("dateDelivery")
            if not delivery_date:
                delivery_date = ""
            
            shipping_option = ShippingOption(
                    shipment_id=shipment_id,
                    method_id=shipment_method.get("methodID"),
                    check_id=shipment_method.get("checkID"),
                    carrier_name=shipment_method.get("carrier").get("name"),
                    service_level_name=shipment_method.get("serviceLevel").get("name"),
                    service_level_description=shipment_method.get("serviceLevel").get("description"),
                    delivery_date=delivery_date,
                    date_pickup=shipment_method.get("datePickup"),
                    buy_price=shipment_method.get("buy_price"),
                    sell_price=shipment_method.get("price")
                )
            
            return shipping_option
            
        except DeliveryMatchException as e:
            self._logger.error(e)
            raise DeliveryMatchException(e)           
        
        except Exception as e:    
            self._logger.error(e)
            self._logger.error(traceback.format_exc())
            raise Exception("Something went wrong while getting shipping options from DeliveryMatch")
    

    def validate_shipment_options_response(self, response):
        try:
            self._logger.info("Validating shipment options response...")
            self._logger.info(f"response= {str(response)}")

            if "status" in response and "code" in response and "message" in response:
                if response["code"] != 30 and response["status"] != "success":
                    self._logger.error(response["message"])
                    api_error_message = f"DeliveryMatch API error: {response['message']}"
                    
                    if "errors" in response:
                        api_error_message = f"DeliveryMatch API error: {response['message']} - {response['errors']}"
                    
                    raise DeliveryMatchException(api_error_message)
                
                # if "all" in response["shipmentMethods"] and len(response["shipmentMethods"]["all"]) == 0:                    
                #     raise DeliveryMatchException("During the selection of shipping options, it was discovered that there were no carriers currently available.")

                # if "methodID" not in response["shipmentMethods"]["lowestPrice"]:
                #     raise DeliveryMatchException("During the selection of shipping options, it was discovered that there were no carriers currently available.")
            else:
                raise DeliveryMatchException("An issue occurred during the request for shipping options from DeliveryMatch.")
            
        except DeliveryMatchException as e:
            raise DeliveryMatchException(e)    
        
        except Exception as e:
            self._logger.error(e)
            self._logger.error(traceback.format_exc())
            self._logger.error(f"DeliveryMatch API response: {str(response)}")
            raise Exception("Something went wrong in the validation of the shipment options response")


    def validate_booking_response(self, response, shipment_to_hub=False):
        try:
            self._logger.info("Validating booking response...")
            if "status" in response and "code" in response and "message" in response:
                if response["status"] != "booked" and response["code"] != 7 and shipment_to_hub == False:
                    self._logger.error(response["message"])
                    self._logger.error(f"DeliveryMatch API response: {str(response)}")                    
                    raise DeliveryMatchException(f"Invalid API response from DeliveryMatch server: {response['message']}")
                
                if response["status"] != "failure" and response["code"] != 72 and shipment_to_hub == True:
                    self._logger.error(response["message"])
                    self._logger.error(f"DeliveryMatch API response: {str(response)}")   
                    raise DeliveryMatchException(f"Invalid API response from DeliveryMatch server: {response['message']}")
            else:
                raise DeliveryMatchException("Invalid response from server.")

            self._logger.info("Validation of booking response successful.")
        except DeliveryMatchException as e:
            self._logger.info(f"DeliveryMatch API response: {str(response)}")

            raise DeliveryMatchException(e)
        
        except Exception as e:    
            self._logger.error(e)  
            self._logger.error(traceback.format_exc())     
            self._logger.info(f"DeliveryMatch API response: {str(response)}")

            raise Exception("Something went wrong in the validation of the booking response")

            
    def get_tracking_url(self, response):
        self._logger.info("Retrieving tracking url from response...")

        tracking_url = response["delivery"]["trackingURL"]

        if not tracking_url:
            tracking_url = "Tracking link is currently unavailable."

        self._logger.info("Retrieving tracking url from response done")
        return tracking_url

    
    def validate_booking_response_v1(self, response):
        self._logger.info("Validating booking response...")
        self._logger.info(f"response= {str(response)}")

        if "status" in response and "code" in response and "message" in response:
            if response["status"] != "booked" and response["code"] != 7:
                self._logger.info(f"Unable to book the shipment {response['message']}")
                return response["message"]
            else:
                return True
        else:
            return "An issue occurred during booking the order in DeliveryMatch."


    def validate_shipment_option_response(self, response):
        self._logger.info("Validating shipment options response...")
        self._logger.info(f"response= {str(response)}")

        if "status" in response and "code" in response and "message" in response:
            if response["code"] != 30 and response["status"] != "success":
                self._logger.info(response["message"])
                return response["message"]

            if "methodID" not in response["shipmentMethods"]["lowestPrice"]:
                return "During the selection of shipping options, it was discovered that there were no carriers currently available."
        else:
            return "An issue occurred during the request for shipping options from DeliveryMatch."

        return True


    def updateShipmentMethod(
        self, shipmentId: int, orderNumber: int, methodId: str, deliveryDate: str
    ):
        self._logger.info("Updating shipment method...")
        url = f"{self.base_url}/updateShipmentMethod"
        body = json.dumps(
            {
                "shipment": {"id": shipmentId, "orderNumber": orderNumber},
                "shipmentMethod": {"id": methodId, "date": deliveryDate},
            }
        )

        self._logger.info(f"base_url={url}")
        self._logger.info(f"headers={self.headers}")
        self._logger.info(f"data={body}")
        response = requests.request("POST", url, headers=self.headers, data=body)
        return response.text
    

    def has_ordernumber_in_dm(self, order_number) -> bool:
        self._logger.info("Checking if order number  is in DM...")
        response = self.get_shipment_by_ordernumber(order_number)

        if "shipment" in response:
            self._logger.info("Order number found in DM")
            return True
        else:
            self._logger.info("Order number not found in DM")
            return False
        
        
    def has_shipment_id_in_dm(self, shipment_id) -> bool:
        try:
            self._logger.info("Checking if shipment id  is in DM...")
            response = self.get_shipment_by_shipment_id(shipment_id)

            if "shipment" in response:
                self._logger.info("shipment number found in DM")
                return True
            else:
                self._logger.info("shipment number NOT found in DM")
                return False
        except Exception as e:
            self._logger.error("Something went wrong in has_shipment_id_in_dm")
            self._logger.error(traceback.format_exc())
            return False
            

    def get_shipment_by_ordernumber(self, order_number, return_shipment_id=False):
        try:
            self._logger.info(
                f"getting shipment by order ID [order_number: {order_number}]"
            )
            body = json.dumps({"shipment": {"orderNumber": order_number}})
            self._logger.info(f"Send GET request to DM [{self.base_url}/getShipment]")

            raw_response = requests.request(
                "GET", f"{self.base_url}/getShipment", headers=self.headers, data=body
            )
            self._logger.info(f"response: {raw_response.text}")

            response = json.loads(raw_response.text)

            if return_shipment_id == True:
                return response["shipment"]["shipmentID"]

            return response
        except Exception as e:
            self._logger.error(f"Error in get_shipment_by_ordernumber: {e}")
            return None


    def get_shipment_by_shipment_id(self, shipment_id, return_shipment_id=False):
        try:
            self._logger.info("Requesting shipment from DM with shipment_id")

            body = json.dumps({"shipment": {"id": shipment_id}})
            raw_response = requests.request("GET", f"{self.base_url}/getShipment", headers=self.headers, data=body)
            response = json.loads(raw_response.text)
           
            self._logger.info("Requesting shipment done.")
            self._logger.info(f"response: {raw_response.text}")
            
            if return_shipment_id == True:
                if("shipment" not in response): return None
                return response["shipment"]["shipmentID"]

            return response
        except Exception as e:
            self._logger.error("Invalid response")
            self._logger.error(traceback.format_exc())            
            self._logger.info(response)
            raise Exception("invalid response")
            

    def shipment_booked_by_ordernumber(self, order_number) -> bool:
        try:
            self._logger.info("Validate if order is booked in DM...")

            response = self.get_shipment_by_ordernumber(order_number)
            if "shipment" not in response:
                self._logger.info("Order not booked in DM")
                return False

            if "status" not in response["shipment"]:
                self._logger.info("Order not booked in DM")
                return False

            if "status" in response["shipment"]:
                if response["shipment"]["status"].lower() != "booked":
                    self._logger.info("Order not booked in DM")
                    return False

            self._logger.info("Order  booked in DM")
            return True
        except DeliveryMatchException as e:
            self._logger.error(
                f"Something went wrong while checking if shipment was booked in DeliveryMatch"
            )
            raise DeliveryMatchException(
                "Something went wrong while checking if shipment was booked in DeliveryMatch"
            )


    def check_credentials(self):
        self._logger.info("checking credentials..")
        if not self.client_id or not self.api_key or not self.base_url:
            self._logger.error("BaseUrl APIKey or ClientId is empty")
            raise ValueError(
                """The Base URL, API key or client ID cannot be empty and must be checked to ensure they are correct.

Please check that you have provided a valid base URL ,API key and client ID. All values cannot be empty and must be entered correctly in order to authenticate access for DeliveryMatch services.

If you are unsure whether your base URL, API key or client ID is correct, please refer to the documentation.
            """
            )
        else:
            try:
                url = f"{self.base_url}/me"

                raw_response = requests.request("GET", url, headers=self.headers)
                response = json.loads(raw_response.text)

                if (
                    "code" in response
                    and response["code"] == 0
                    and response["message"] == "Page not found."
                ):
                    self._logger.error("BaseUrl not found")

                    raise Exception("Please check the base url in the config")

                if "code" in response and response["code"] != 150:
                    self._logger.error("incorrect credentials")
                    raise Exception(
                        f"API repsonse: {response['message']} Please check in the config if credentials are correct."
                    )

            except Exception as e:
                self._logger.error(f"Error in {self.check_credentials.__name__}: {e}")
                # self._logger.error(response.text)
                raise Exception(e)

        self._logger.info("Valid Credentials!")
