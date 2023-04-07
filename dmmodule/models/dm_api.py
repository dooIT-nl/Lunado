import requests, json


class DmApi:

    def __init__(self, base_url,  api_key, client_id):
        self.base_url = base_url
        self.client_id = client_id
        self.api_key = api_key
        self.headers = {
            'apikey': api_key,
            'client': str(client_id),
            'Content-Type': 'application/json'
        }        
        self.channel = "Odoo testing"
        self.check_credentials()


    def postToDeliveryMatchShipment(self,
        orderNumber, customerRef, incoterm, customerNote,
        customerId, customerName, customerCompanyName,
        customerAddress1, customerAddress2, customerStreet,
        customerPostcode, customerCity, customerCountry,
        customerPhone, customerEmail, products,
        isFragile, isDangerous, priceIncl,
        priceExcl, totalWeight,
        actionBook = False, updateShipment=False, shipmentId=None, status="new", return_raw=True):
    
        action = "show"
        url = f"{self.base_url}/insertShipment"


        if self.has_ordernumber_in_dm(orderNumber) == True:
            updateShipment = True
            shipmentId = self.get_shipment_by_ordernumber(orderNumber)["shipment"]["shipmentID"]


        if actionBook:
            action = "book"


        if updateShipment:
            url = f"{self.base_url}/updateShipment"
    
        
        body = json.dumps({
            "client": {
                "id": self.client_id,
                "channel": self.channel,
                "action": action
            },
            "shipment": {
                "id": shipmentId,
                "status": status,
                "orderNumber": orderNumber,
                "reference": customerRef,
                "language": "EN",
                "currency": "EUR",
                "inbound": False,
                "incoterm": incoterm,
                "note": customerNote,
            },
            "customer": {
                "id": customerId,
                "address": {
                "name": customerName,
                "companyName": customerCompanyName,
                "address1": customerAddress1,
                "address2": customerAddress2,
                "street": customerStreet,
                "postcode": customerPostcode,
                "city": customerCity,
                "country": customerCountry,
                },
                "contact": {
                "phoneNumber": customerPhone,
                "email": customerEmail
                }
            },
            "quote": {
                "product": products
            },
            "fragileGoods": isFragile,
            "dangerousGoods": isDangerous,
            "priceIncl": priceIncl,
            "priceExcl": priceExcl,
            "weight": totalWeight
            })

        response = requests.request("POST", url, headers=self.headers, data=body)


        if return_raw:
            return response.text
        
        return json.loads(response.text)

    
    def get_tracking_url(self, response):
        tracking_url = response["delivery"]["trackingURL"]
            
        if not tracking_url: 
            tracking_url = "Tracking link is currently unavailable."
        
        return tracking_url

    
    
    def validate_booking_response(self, response):
        if "status" in response and "code" in response and "message" in response:
            if response["status"] != "booked" and response["code"] != 7:
                return response["message"]
            else:
                return True
        else:
            return "An issue occurred during booking the order in DeliveryMatch."
   
   
    def validate_shipment_option_response(self, response):
        
        if "status" in response and "code" in response and "message" in response:
            if (response["code"] != 30 and response["status"] != "success"):
                return response["message"]

            if "methodID" not in response["shipmentMethods"]["lowestPrice"]:
                return "During the selection of shipping options, it was discovered that there were no carriers currently available."
        else:
            return "An issue occurred during the request for shipping options from DeliveryMatch."

        return True


    def updateShipmentMethod(self, shipmentId:int, orderNumber:int, methodId:str, deliveryDate:str):

        url = f"{self.base_url}/updateShipmentMethod"
        body = json.dumps({
            "shipment": {
                "id": shipmentId,
                "orderNumber": orderNumber
            },
            "shipmentMethod": {
                "id": methodId,
                "date": deliveryDate
            }
        })

        response = requests.request("POST", url, headers=self.headers, data=body)
        return response.text


    def has_ordernumber_in_dm(self, order_number):
        response = self.get_shipment_by_ordernumber(order_number)

        if "shipment" in response:
            return True
        else:
            return False

    
    def get_shipment_by_ordernumber(self, order_number):
        body = json.dumps({
            "shipment": {
                "orderNumber": order_number
            }
        })
        raw_response = requests.request("GET", f"{self.base_url}/getShipment", headers=self.headers, data=body)
        response = json.loads(raw_response.text)

        return response


    def get_shipment_by_shipment_id(self, shipment_id):
        body = json.dumps({
            "shipment": {
                "id": shipment_id
            }
        })
        raw_response = requests.request("GET", f"{self.base_url}/getShipment", headers=self.headers, data=body)
        response = json.loads(raw_response.text)
        return response
    
    def shipment_booked_by_ordernumber(self, order_number) -> bool:
        response = self.get_shipment_by_ordernumber(order_number)
        if "shipment" not in response:
            return False

        if "status" not in response["shipment"]:
            return False

        if "status" in response["shipment"]:
            if response["shipment"]["status"].lower() != "booked":
                return False

        return True
    
    
    def check_credentials(self):
        if not self.client_id or not self.api_key or not self.base_url:
            raise ValueError("""The Base URL, API key or client ID cannot be empty and must be checked to ensure they are correct.

Please check that you have provided a valid base URL ,API key and client ID. All values cannot be empty and must be entered correctly in order to authenticate access for DeliveryMatch services.

If you are unsure whether your base URL, API key or client ID is correct, please refer to the documentation.
            """)
        else:
            try:
                url = f"{self.base_url}/me"

                raw_response = requests.request("GET", url, headers=self.headers)
                response = json.loads(raw_response.text)
                
                if "code" in response and response["code"] == 0 and response["message"] == "Page not found.":
                    raise ValueError("Please check the base url in the config")
                
                
                if "code" in response and response["code"] != 150:
                    raise ValueError(f"API repsonse: {response['message']} Please check in the config if credentials are correct.")
                
            except ValueError as e:
                raise ValueError(e)
                
                


        

