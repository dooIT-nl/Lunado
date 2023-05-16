import json, logging, traceback
import requests
import base64
from .dm_api import DmApi
from .helper import Helper
from .deliverymatch_exception import DeliveryMatchException
from odoo.tools import html2plaintext

class OdooDb:    
    def __init__(self, odoo_env):
        self.odoo_env = odoo_env
        self._logger = logging.getLogger("DeliveryMatch - OdooDb")

    # deliverOptions dict: carrierName, serviceLevelName, serviceLevelDescription, deliveryDate, buyPrice, price, shipmentId, odooOrderId
    def insert_into_deliver_options(self, deliverOptions):
        try:
            self._logger.info("inserting shipping options from DM to Odoo dm.deliver.options table")
            for i in deliverOptions:
                self.odoo_env.env['dm.deliver.options'].create(
                    {
                        'carrierName': i.get("carrierName"),
                        'serviceLevelName': i.get("serviceLevelName"),
                        'serviceLevelDescription': i.get("serviceLevelDescription"),
                        'deliveryDate': i.get("deliveryDate"),
                        'dm_pickup_date': i.get("datePickup"),
                        'buyPrice': i.get("buyPrice"),
                        'price': i.get("price"),
                        'shipmentId': i.get("shipmentId"),
                        'odooOrderId': i.get("odooOrderId"),
                        'methodId': i.get('methodId'),
                        'checkId': i.get('checkId')
                    }
                )
            self._logger.info("Insertion process finished successfully")
        except Exception as e:
            self._logger.error(f"An error occurred while inserting shipping options in Odoo: {e}")
            raise Exception("An error occurred while fetching the shipping options")

    def hasOdooOrderId(self, id:int):
        try:
            self._logger.info("Checking if odoo_id is in dm.deliver.options")
            foundIds = self.odoo_env.env['dm.deliver.options'].search([('odooOrderId', '=', id)])

            if not foundIds:
                self._logger.info("odoo_id not found in dm_deliver.options")
                return False
            else:
                self._logger.info("odoo_id found in dm_deliver.options")

                return True
        except Exception as e:
            self._logger.error(f"An error occurred while checking if odoo_id is in dm.deliver.options: {e}")
            raise Exception("There was an error encountered during the process")

    # def getCountryFromDB(self, country_id, state_id):
    #     print(country_id)
    #     print(state_id)
    #     state = self.env['res.country.state'].search([('country_id', '=', country_id)])
    #     return state

    def deleteDeliveryOptionsByOrderId(self, id:int):
        try: 
            self._logger.info("Deleting shipping option from dm.deliver.options")
            if self.hasOdooOrderId(id):
                self.odoo_env.env["dm.deliver.options"].search([('odooOrderId','=',id)]).unlink()
            
            self._logger.info("Shipping option deleted")
        except Exception as e:
            self._logger.error(f"An error occurred while deleting shipping options from dm.deliver.options: {e}")
            raise Exception("Failed to remove a shipping option from the shipping options table")
        


class SaleOrderHandler:

    def __init__(self, odoo_env, base_url, api_key, client_id, override_product_length, delivery_option_preference=None, currency=None):
        self.odoo_env = odoo_env
        self.db = OdooDb(odoo_env)
        self.api = DmApi(base_url, api_key, client_id)
        self.delivery_option_preference = delivery_option_preference
        self.helper = Helper()
        self.currency = currency
        self.override_product_length = override_product_length
        self._logger = logging.getLogger("DeliveryMatch - SaleOrderHandler")

    

    def get_delivery_options(self, order_number, customer, order_lines, incoterm, warehouse, manual=False, preference=False):
        
        try:
            self._logger.info("Retrieving shipping options...")
            display_number = self.odoo_env.display_name            
            
            if(self.api.shipment_booked_by_ordernumber(display_number) == True):
                raise DeliveryMatchException("Your order has already been booked in DeliveryMatch. Please check its status on your DeliveryMatch dashboard.")

            
            order_number = order_number
            is_company = customer.is_company
            customer_id = customer.id
            customer_name = customer.name
            customer_company_name = customer.parent_id.name
            customer_ref = self.odoo_env.client_order_ref
            customer_note = html2plaintext(customer.comment)
            address1 = customer.street
            address2 = customer.street2
            street = customer.street
            postcode = customer.zip
            city = customer.city
            country = customer.country_code
            phone = customer.phone
            email = customer.email
            self._logger.info(f"{self.get_delivery_options.__name__}: getting order information for DeliveryMatch API")

            self._logger.info("checking if company is true")            
            if is_company == True:
                customer_company_name = customer_name     
                customer_name = ""       

            self._logger.info("validating required fields...")
            fields_filled =  self.helper.validate_required_fields(
                {
                 "Address": address1,
                 "Street": street,
                 "Zipcode": postcode,
                 "City": city,
                 "Country": country,
                 "Phone number": phone,
                 "Email": email,
                 "Warehouse": warehouse.name
                 },
                "must be filled in order to request shipping options from DeliveryMatch."
            )
            
            if fields_filled != True:
                raise Exception(fields_filled) 
            
            if not incoterm:
                raise Exception("Incoterm cannot be empty.")
            
            
            product_attributes_filled  = self.product_validation(order_lines)
            if product_attributes_filled != True:
                raise Exception(product_attributes_filled)
                        
            
            products: tuple = self.format_products(order_lines)

            is_fragile = self.has_fragile_products()
            is_dangerous = self.has_dangerous_products()

            total_price_taxed = self.helper.order_total_price(self.odoo_env._origin.order_line, True)
            total_price_exc_vat = ""
            total_weight = self.total_products_weight()


            response = self.api.postToDeliveryMatchShipment(
                display_number, customer_ref, incoterm, customer_note, customer_id, customer_name, customer_company_name,
                address1, address2, street, postcode, city, country, phone, email, products, is_fragile, is_dangerous,
                total_price_taxed, total_price_exc_vat, total_weight
            )

            valid_response = self.api.validate_shipment_option_response(json.loads(response))
            if valid_response != True:
                raise Exception(valid_response)

            if manual:
                # retrieving the deliveryOptions from DeliveryMatch API response formatting it
                # and inserting into Odoo Database
                deliveryOptions = self.format_delivery_options(data=response)
                self.db.deleteDeliveryOptionsByOrderId(order_number)
                self.db.insert_into_deliver_options(deliveryOptions)
                return True
            
            if preference != False:
                dm_delivery_option = self.format_delivery_options_on_preference(response, preference)
                
                self.api.updateShipmentMethod(dm_delivery_option.get("shipmentId"), self.odoo_env._origin.id, dm_delivery_option.get("methodId"), dm_delivery_option.get("deliveryDate"))
                self.update_sale_order(dm_delivery_option)
                return True

        except Exception as e:
            self._logger.error(f"Error in {self.get_delivery_options.__name__}: {e}")
            # return "Something went wrong while requesting shipment options from DeliveryMatch"
            raise DeliveryMatchException(e)
            

    def has_fragile_products(self, order_line=None) -> bool:
        try: 
            self._logger.info("Checking for fragile products...")
            order_line = self.odoo_env.order_line
            
            if order_line != None:
                order_line = order_line
            
            
            for p in order_line:
                productObj = p.product_template_id

                if productObj.dm_is_fragile:
                    return True

            return False
        except Exception as e:
            tb = traceback.format_exc()
            self._logger.error(f"{e} \n{tb}")
            raise Exception("An error occurred while verifying if the products are fragile")



    def has_dangerous_products(self, order_line=None) -> bool:
        try:
            self._logger.info("Checking for dangerous products...")

            order_line = self.odoo_env.order_line

            if order_line != None:
                order_line = order_line
            
            
            for p in order_line:
                productObj = p.product_template_id

                if productObj.dm_is_dangerous:
                    return True

            return False
        except Exception as e:
            tb = traceback.format_exc()
            self._logger.error(f"{e} \n{tb}")            
            raise Exception("An error occurred while verifying if the products are dangerous")
            

 
    def total_products_weight(self, order_line=None) -> float:
        self._logger.info("Summing up the total weight of the order...")
        try:
            order_line = self.odoo_env.order_line

            if order_line != None:
                order_line = order_line
            
            # WEIGHT IN KG
            totalWeight = 0

            for p in order_line:
                productObj = p.product_template_id

                quantity = int(p.product_uom_qty)
                weight = productObj.weight * quantity
                totalWeight += weight
            
            return round(totalWeight,2)
        except Exception as e:
            tb = traceback.format_exc()
            self._logger.error(f"{e} \n{tb}")            
            raise Exception("Failed to calculate the total weight of the products.")


    def product_validation(self, order_lines):
        self._logger.info("Validatinig product format...")
        try:
            if len(order_lines) == 0:
                return "Sale order must contain items in order to use DeliveryMatch services."
            
            for p in order_lines:
                product_line = p.product_template_id
                quantity = int(p.product_uom_qty)
                weight = product_line.weight
                price = p.price_unit
                
                filled_product_attributes = self.helper.validate_required_fields(
                    {"Weight": weight,
                    "Length": product_line.dm_length,
                    "Width": product_line.dm_width,
                    "Height": product_line.dm_height,
                    "Value": price,
                    "Product quantity": quantity,
                    "Product name": product_line.name,
                    "Barcode (EAN)": product_line.barcode,
                    "SKU": product_line.dm_sku,
                    },
                    f"must have a value in the product '{product_line.name}' in order to use DeliveryMatch services, you can find this required field on the 'Products' page."
                )
                return filled_product_attributes
                
            return True
        except Exception as e:
            tb = traceback.format_exc()
            self._logger.error(f"{e} \n{tb}")
            raise Exception("An error occurred during product validation.")
            

    def has_product_in_stock(self, product_id, quantity, stock_location_id) -> bool:
        self._logger.info("Checking if product is in stock...")
        
        try:
            stock_product = self.odoo_env.env['stock.quant'].search([('product_tmpl_id.id', '=', product_id), ('location_id', '=', stock_location_id)])
            
            if stock_product.available_quantity < quantity:
                return False

            if not stock_product.available_quantity:
                return False
            
            return True
        except Exception as e:
            tb = traceback.format_exc()
            self._logger.error(f"{e} \n{tb}")
            raise Exception("Failed to check product availability in stock.")


    def format_products(self, order_lines, is_external_warehouse=False) -> tuple:
        try:
            self._logger.info("formatting products in DM format")
            products = []
            
            has_x_studio_length = self.helper.has_sale_order_custom_length(order_lines)


            for p in order_lines:
                product_line = p.product_template_id
                quantity = int(p.product_uom_qty)
                weight = product_line.weight
                price = p.price_unit
                length = product_line.dm_length

                if (has_x_studio_length == True and self.override_product_length and length > 0):
                    length = p.x_studio_length
                
                stock_location_id = self.odoo_env.warehouse_id.lot_stock_id.id
                product_template_id = product_line.id
                in_stock = self.has_product_in_stock(product_template_id, quantity, stock_location_id)

                if is_external_warehouse:
                    if self.odoo_env.warehouse_id.dm_external_warehouse:
                        external_warehouse_id = self.odoo_env.warehouse_id.warehouse_options
                else:
                    external_warehouse_id = None

                hscode = product_line.dm_hscode
                country_origin = product_line.dm_country_origin

                if not hscode: hscode = None
                if not country_origin: country_origin = None

                
                product =  {
                    "weight": weight,
                    "length": product_line.dm_length,
                    "width": product_line.dm_width,
                    "height": product_line.dm_height,
                    "stock": in_stock,
                    "value": price,
                    "warehouse": external_warehouse_id,
                    "quantity": quantity,
                    "description": p.name,
                    "content": product_line.name,
                    "SKU": product_line.dm_sku,
                    "EAN": product_line.barcode,
                    "hsCode": hscode,
                    "countryOfOrigin": country_origin
                }

                products.append(product)
                
            return tuple(products)
        except Exception as e:
            tb = traceback.format_exc()
            self._logger.error(f"{e} \n{tb}")
            raise Exception("Failed to format the products. ")
    


    def update_sale_order(self, dm_delivery_option:dict):
        try:
            self._logger.info("updating sale order...")   
            current_sale_order = self.odoo_env.env['sale.order'].search([('id', '=', self.odoo_env._origin.id)])
            current_sale_order.dm_shipment_id = dm_delivery_option.get("shipmentId")
    
            current_sale_order.dm_carrierName = dm_delivery_option.get("carrierName")
            current_sale_order.dm_serviceLevelName = dm_delivery_option.get("serviceLevelName")
            current_sale_order.dm_serviceLevelDescription = dm_delivery_option.get("serviceLevelDescription")
            current_sale_order.dm_deliveryDate = dm_delivery_option.get("deliveryDate")
            current_sale_order.dm_pickup_date = dm_delivery_option.get("pickupDate")
    
            current_sale_order.dm_buyPrice = dm_delivery_option.get("buyPrice")
            current_sale_order.dm_price = dm_delivery_option.get("price")
            
            current_sale_order.dm_methodId = dm_delivery_option.get("methodId")
            current_sale_order.dm_checkId = dm_delivery_option.get("checkId")
            current_sale_order.shipmentURL = f"{current_sale_order.dm_shipment_url}{dm_delivery_option.get('shipmentId')}"
            current_sale_order.delivery_option_selected = True
        except Exception as e:
            tb = traceback.format_exc()
            self._logger.error(f"{e} \n{tb}")
            raise Exception("Failed to update the sale order.")


    def format_delivery_options(self, data):
        try: 
            self._logger.info("Formating shipping options from DM...")
            data = json.loads(data)

            deliverOptions= []
            shipmentId = data["shipmentID"]
            shipmentMethods: dict = data["shipmentMethods"]["all"]

            for key in shipmentMethods:

                shipmentMethod: dict =  shipmentMethods.get(key)
                
                for method in shipmentMethod:
                    methodId = method.get("methodID")
                    checkId = method.get("checkID")
                    carrierName = method.get("carrier").get("name")
                    serviceLevelName = method.get("serviceLevel").get('name')
                    serviceLevelDescription = method.get("serviceLevel").get('description')
                    deliveryDate = method.get("dateDelivery")
                    datePickup = method.get("datePickup")
                    
                    buyPrice = method.get("buy_price")
                    price = method.get("price")

                    deliverOption = {
                        "carrierName": carrierName,
                        "serviceLevelName": serviceLevelName, 
                        "serviceLevelDescription": serviceLevelDescription,
                        "deliveryDate": deliveryDate,
                        "datePickup": datePickup,
                        "buyPrice": buyPrice,
                        "price": price,
                        "shipmentId": shipmentId,
                        "odooOrderId": self.odoo_env.id,
                        "methodId": methodId,
                        "checkId": checkId
                    }

                    deliverOptions.append(deliverOption)
            
            return deliverOptions
        except Exception as e:
            tb = traceback.format_exc()
            self._logger.error(f"{e} \n{tb}")
            raise Exception("Failed to update the shipping options.")

    
    def format_delivery_options_on_preference(self, response, preference) -> dict:
        try:
            response = json.loads(response)

            if preference == "lowest":
                delivery_preference = "lowestPrice"
            elif preference == "earliest":
                delivery_preference = "earliest"
            elif preference == "most_green":
                delivery_preference = "greenest"
                
            if delivery_preference not in response["shipmentMethods"]:
                delivery_preference = "lowestPrice"
                self.odoo_env._origin.message_post(body="To ensure that you receive the most environmentally-friendly delivery option, please specify this preference with Big Mile. In this case, we have chosen the lowest-priced option.")
                
            

            shipment_id = response["shipmentID"]
            shipment_method: dict = response["shipmentMethods"][delivery_preference]
            
            if "carrier" not in shipment_method:
                return False

            return {            
                "carrierName": shipment_method.get("carrier").get("name"),
                "serviceLevelName": shipment_method.get("serviceLevel").get('name'),
                "serviceLevelDescription": shipment_method.get("serviceLevel").get('description'),
                "deliveryDate": shipment_method.get("dateDelivery"),
                "pickupDate": shipment_method.get("datePickup"),
                "buyPrice": shipment_method.get("buy_price"),
                'price': shipment_method.get('price'),
                "shipmentId": shipment_id,
                "methodId": shipment_method.get("methodID"),
                "checkId": shipment_method.get("checkID")
            }
        except Exception as e:
            tb = traceback.format_exc()
            self._logger.error(f"{e} \n{tb}")
            raise Exception("During the auto-selection of shipping options, it was discovered that there were no carriers currently available.")
        
    
    def book_order_dm(self, order_number, incoterm, customer_ref, customer_note, customer_name, company_name, address1, street, country, city, zipcode, customer_id,
                      customer_email, customer_phone, order_line, price_inc, pric_exc, address2=False):
        
        try:
            
            if (self.api.shipment_booked_by_ordernumber(order_number) == True):
                raise ValueError(f"Order({order_number}) is already booked in DeliveryMatch.")
            
            total_price_taxed = self.helper.order_total_price(order_line, True)
            
            raw_response = self.api.postToDeliveryMatchShipment(
                orderNumber=self.odoo_env.display_name,
                incoterm=incoterm,
                customerRef=customer_ref,
                customerNote=customer_note,
                customerName=customer_name,
                customerCompanyName=company_name,
                customerAddress1=address1,
                customerAddress2=address2,
                customerStreet=street,
                customerCountry=country,
                customerCity=city,
                customerPostcode=zipcode,
                customerId=customer_id,
                customerEmail=customer_email,
                customerPhone=customer_phone,
                products=self.format_products(order_line),
                isFragile=self.has_fragile_products(order_line=order_line),
                isDangerous=self.has_dangerous_products(order_line=order_line),
                priceIncl=total_price_taxed,
                priceExcl="",
                totalWeight=self.total_products_weight(order_line=order_line),
                actionBook=True
            )
            
            response = json.loads(raw_response)
            if "status" in response and "code" in response and "message" in response:
                if response["status"] != "booked" and response["code"] != 7:
                    raise Exception(response["message"])
            else:
                raise Exception("An issue occurred during booking the order in DeliveryMatch.")
            
            current_sale_order = self.odoo_env.env['sale.order'].search([('id', '=', order_number)])
            
            response_tracking_url = response["delivery"]["trackingURL"]
            if not response_tracking_url: 
                response_tracking_url = "Tracking link is currently unavailable."
            
            current_sale_order.shipment_tracking_url = response_tracking_url
            
            label_response = requests.get(response["labelURL"])
            shipment_label = base64.b64encode(label_response.content).decode()
            current_sale_order.shipment_label_attachment = shipment_label
            return True
            
        except Exception as e:
            tb = traceback.format_exc()
            self._logger.error(f"{e} \n{tb}")
            raise Exception("An error occurred while booking the shipment. ")

      
    def validate_order(self, customer, sale_order, operation_lines, dm_order_number):
        fields_filled = self.helper.validate_required_fields(
            {
                "Address": customer.street,
                "Street": customer.street,
                "Zipcode": customer.zip,
                "City": customer.city,
                "Country": customer.country_code,
                "Phone number": customer.phone,
                "Email": customer.email
            },
            "must be filled in order to request shipping options from DeliveryMatch."
        )

        if fields_filled != True:
            return fields_filled

        if not sale_order.incoterm.code:
            return "Incoterm cannot be empty. Check Sale Order"

        product_attributes_filled = self.product_validation(operation_lines)
        if product_attributes_filled != True:
            return product_attributes_filled

        if self.api.shipment_booked_by_ordernumber(dm_order_number) == True:
            return "Your order has already been booked in DeliveryMatch. Please check its status on your DeliveryMatch dashboard."

        return True


    def send_order_to_hub(self):
        try:
            order_number = self.odoo_env._origin.id
            customer_id = self.odoo_env.partner_id.id
            customer = self.odoo_env.partner_id
            customer_name = customer.name
            customer_company_name = customer.parent_id.name
            customer_ref = self.odoo_env.client_order_ref
            customer_note = html2plaintext(customer.comment)
            address1 = customer.street
            address2 = customer.street2
            street = customer.street
            postcode = customer.zip
            city = customer.city
            country = customer.country_code
            phone = customer.phone
            email = customer.email            
            incoterm = self.odoo_env.incoterm.code

            if customer.is_company == True:
                customer_company_name = customer_name     
                customer_name = None   
            
            valid_order = self.validate_order(customer, self.odoo_env, self.odoo_env.order_line, self.odoo_env.id)            
            if valid_order != True:
                return valid_order
            
            if not self.odoo_env.delivery_option_selected:
                return "Choosing a shipping option is mandatory before booking an order."
            
            
            products: tuple = self.format_products(self.odoo_env.order_line, True)

            isFragile = self.has_fragile_products()
            isDangerous = self.has_dangerous_products()

            total_price_taxed = self.helper.order_total_price(self.odoo_env._origin.order_line, True)
            totalPriceExclVat = ""
            totalWeight = self.total_products_weight()
            

            response = self.api.postToDeliveryMatchShipment(
                order_number, customer_ref, incoterm, customer_note, customer_id, customer_name, customer_company_name,
                address1, address2, street, postcode, city, country, phone, email, products, isFragile, isDangerous,
                total_price_taxed, totalPriceExclVat, totalWeight, actionBook=True
            )

            valid_booking =  self.api.validate_booking_response(json.loads(response))
            if valid_booking != True:
                return valid_booking
            
            return True
        except Exception as e:
            tb = traceback.format_exc()
            self._logger.error(f"{e} \n{tb}")
            raise Exception("An error occurred while sending the shipment to the HUB.HUB")
