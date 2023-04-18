import json
import traceback
import requests
import base64
from .dm_api import DmApi
from .helper import Helper
from odoo.tools import html2plaintext


class OdooDb:    
    def __init__(self, odoo_env):
        self.odoo_env = odoo_env

    def insert_into_deliver_options(self, deliverOptions):
        for i in deliverOptions:
            self.odoo_env.env['dm.deliver.options'].create(
                {
                    'carrierName': i.get("carrier_name"),
                    'serviceLevelName': i.get("service_level_name"),
                    'serviceLevelDescription': i.get("service_level_description"),
                    'deliveryDate': i.get("delivery_date"),
                    'dm_pickup_date': i.get("date_pickup"),
                    'buyPrice': i.get("buy_price"),
                    'price': i.get("price"),
                    'shipmentId': i.get("shipment_id"),
                    'odooOrderId': i.get("odoo_order_id"),
                    'methodId': i.get('method_id'),
                    'checkId': i.get('check_id')
                }
            )

    def hasOdooOrderId(self, id:int):
        foundIds = self.odoo_env.env['dm.deliver.options'].search([('odooOrderId', '=', id)])

        if not foundIds:
            return False
        else:
            return True


    def deleteDeliveryOptionsByOrderId(self, id:int):
        if self.hasOdooOrderId(id):
            self.odoo_env.env["dm.deliver.options"].search([('odooOrderId','=',id)]).unlink()


class StockPickingHandler():
    def __init__(self, base_url, api_key, client_id,override_product_length, odoo_env=None, shipping_preference=None):
        self.odoo_env = odoo_env
        self.api = DmApi(base_url, api_key, client_id)
        self.helper = Helper()
        self.shipping_preference = shipping_preference
        self.db = OdooDb(odoo_env)
        self.override_product_length = override_product_length



    def book_delivery_order(self, operation_lines, sale_order, dm_order_number, customer, dm_shipment_id, book_to_warehouse=False):
        try:

            order_validated = self.validate_order(customer, sale_order, operation_lines, dm_order_number)
            if order_validated != True:
                return order_validated

            is_fragile = self.helper.has_fragile_products(operation_lines)
            is_dangerous = self.helper.has_dangerous_products(operation_lines)
            products = self.format_products(operation_lines, book_to_warehouse)
            total_weight = self.total_products_weight(operation_lines)
            total_price_taxed = self.helper.order_total_price(operation_lines)

            customer_name = customer.name
            customer_company_name = customer.parent_id.name

            if customer.is_company == True:
                customer_company_name = customer_name
                customer_name = None


            response = self.api.postToDeliveryMatchShipment(
                orderNumber=dm_order_number,
                incoterm=sale_order.incoterm.code,
                customerRef=customer.ref,
                customerNote=html2plaintext(customer.comment),
                customerName=customer_name,
                customerCompanyName=customer_company_name,
                customerAddress1=customer.street,
                customerAddress2=customer.street2,
                customerStreet=customer.street,
                customerCountry=customer.country_code,
                customerCity=customer.city,
                customerPostcode=customer.zip,
                customerId=customer.id,
                customerEmail=customer.email,
                customerPhone=customer.phone,
                products=products,
                isFragile=is_fragile,
                isDangerous=is_dangerous,
                priceIncl=total_price_taxed,
                priceExcl="",
                totalWeight=total_weight,
                shipmentId=dm_shipment_id,
                return_raw=False,
                actionBook=True
            )


            valid_booking_response =  self.api.validate_booking_response(response)
            if valid_booking_response != True:
                return valid_booking_response


            delivery_order = self.odoo_env.env['stock.picking'].search([('id', '=', self.odoo_env._origin.id)])
            delivery_order.shipment_tracking_url = self.api.get_tracking_url(response)
            delivery_order.shipment_label_attachment = self.helper.convert_label(response["labelURL"])
            return True

        except Exception as e:
            return "An error occurred while booking your shipment."

        


    def get_shipping_options_delivery_level(self, sale_order_id, operation_lines, sale_order, delivery_id, customer, dm_shipment_id):
        try:
    
            products = self.format_products(operation_lines)
            total_weight = self.total_products_weight(operation_lines)
            is_fragile = self.helper.has_fragile_products(operation_lines)
            is_dangerous = self.helper.has_dangerous_products(operation_lines)
            total_price_taxed = self.helper.order_total_price(operation_lines)



            if not dm_shipment_id:
                if (self.api.has_ordernumber_in_dm(sale_order_id) == False):
                    return f"Shipment with the order-number {sale_order_id} not found in DeliveryMatch."
            
            dm_order_number = f"{sale_order_id}-{delivery_id}"

            
            order_validated = self.validate_order(customer, sale_order, operation_lines, dm_order_number)  
            if order_validated != True:
                return order_validated


            customer_name = customer.name
            customer_company_name = customer.parent_id.name

            if customer.is_company == True:
                customer_company_name = customer_name
                customer_name = None

            response = self.api.postToDeliveryMatchShipment(
                orderNumber=dm_order_number,
                incoterm=sale_order.incoterm.code,
                customerRef=customer.ref,
                customerNote=html2plaintext(customer.comment),
                customerName=customer_name,
                customerCompanyName=customer_company_name,
                customerAddress1=customer.street,
                customerAddress2=customer.street2,
                customerStreet=customer.street,
                customerCountry=customer.country_code,
                customerCity=customer.city,
                customerPostcode=customer.zip,
                customerId=customer.id,
                customerEmail=customer.email,
                customerPhone=customer.phone,
                products=products,
                isFragile=is_fragile,
                isDangerous=is_dangerous,
                priceIncl=total_price_taxed,
                priceExcl="",
                totalWeight=total_weight,
                shipmentId=dm_shipment_id,
                return_raw=False
            )

            
            
            response_validated =  self.api.validate_shipment_option_response(response)

            if response_validated != True:
                return response_validated

            
            # MANUAL SELECTION
            if self.shipping_preference == None:
                formatted_shipping_options = self.helper.format_shipping_options(data=response, odoo_order_id=self.odoo_env._origin.id)
                self.db.deleteDeliveryOptionsByOrderId(self.odoo_env._origin.id)
                self.db.insert_into_deliver_options(formatted_shipping_options)
                return True
            
            #  AUTO-SELECTION
            if self.shipping_preference != None:
                dm_delivery_option = self.format_delivery_options_on_preference(response, self.shipping_preference)
                
                self.api.updateShipmentMethod(dm_delivery_option.get("shipment_id"), delivery_id, dm_delivery_option.get("method_id"), dm_delivery_option.get("delivery_date"))
                self.update_delivery(dm_delivery_option)
                return True
            

        except Exception as e:
            print("__________________________________\n\n\n\n")
            print(e)
            print("__________________________________\n\n\n\n")
            return "Something went wrong while selecting a shipping option."
   

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


    def has_product_in_stock(self, product_id, quantity, stock_location_id) -> bool:
        stock_product = self.odoo_env.env['stock.quant'].search([('product_id.id', '=', product_id), ('location_id', '=', stock_location_id)])
        
        if stock_product.available_quantity < quantity:
            return False

        if not stock_product.available_quantity:
            return False
        
        return True

    


    def format_products(self, operation_lines, is_external_warehouse=False, sale_order=None) -> tuple:
        products = []
        
        # order_line = sale_order.order_line

        for line in operation_lines:
            product = line.product_id
            quantity = line.product_uom_qty
            location_id = self.odoo_env.location_id.id
            in_stock = self.has_product_in_stock(product.id, quantity, location_id)
            length = product.dm_length



            if is_external_warehouse:
                external_warehouse = self.helper.get_external_warehouse_id(self.odoo_env, location_id)
            else:
                external_warehouse = None

            hscode = product.dm_hscode
            country_origin = product.dm_country_origin

            if not hscode: hscode = None
            if not country_origin: country_origin = None

            product_dict = {
                "weight": product.weight,
                "length": length,
                "width": product.dm_width,
                "height": product.dm_height,
                "stock": in_stock,
                "value": product.list_price,
                "warehouse": external_warehouse,
                "quantity": line.product_uom_qty,
                "description": line.name,
                "content": product.name,
                "SKU": product.dm_sku,
                "EAN": product.barcode,
                "hsCode": hscode,
                "countryOfOrigin": country_origin
            }
            
            products.append(product_dict)

            return tuple(products)


    def total_products_weight(self, operation_lines) -> float:
        # WEIGHT IN KG
        totalWeight = 0

        for line in operation_lines:
            product = line.product_id
            quantity = int(line.product_uom_qty)
            weight = product.weight * quantity
            totalWeight += weight

        return round(totalWeight, 2)


    def generate_sub_order_id(self, sale_order_id):
        delivery_num = 1
        while 1:
            dm_order_number = f"{sale_order_id}-{delivery_num}"
            has_shipment_dm = self.api.has_ordernumber_in_dm(order_number=dm_order_number)

            if (has_shipment_dm == True):
                delivery_num += 1
            else:
                break
        
        return dm_order_number

        
    def product_validation(self, operation_lines):
        for line in operation_lines:
            product_line = line.product_id
            quantity = int(line.product_uom_qty)
            weight = product_line.weight
            price = product_line.lst_price

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

            if filled_product_attributes != True:
                return filled_product_attributes

        return True


    def format_delivery_options_on_preference(self, response, preference) -> dict:
        try:

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
            print("______________________________________________________________________\n\n\n\n")
            print(shipment_method)
            print("______________________________________________________________________\n\n\n\n")


            return {
                "carrier_name": shipment_method.get("carrier").get("name"),
                "service_level_name": shipment_method.get("serviceLevel").get('name'),
                "service_level_description": shipment_method.get("serviceLevel").get('description'),
                "delivery_date": shipment_method.get("dateDelivery"),
                "pickup_date": shipment_method.get("datePickup"),
                "buy_price": shipment_method.get("buy_price"),
                'price': shipment_method.get('price'),
                "shipment_id": shipment_id,
                "method_id": shipment_method.get("methodID"),
                "check_id": shipment_method.get("checkID")
            }
        except Exception as e:
            print("__________________________________\n\n\n\n")
            print(e)
            print("__________________________________\n\n\n\n")


    def update_delivery(self, dm_delivery_option:dict):
        try:
            delivery_order = self.odoo_env.env['stock.picking'].search([('id', '=', self.odoo_env._origin.id)])
            delivery_order.dm_shipment_id = dm_delivery_option.get("shipment_id")

            delivery_order.dm_carrier_name = dm_delivery_option.get("carrier_name")
            delivery_order.dm_service_level_name = dm_delivery_option.get("service_level_name")
            delivery_order.dm_service_level_description = dm_delivery_option.get("service_level_description")
            delivery_order.dm_delivery_date = dm_delivery_option.get("delivery_date")
            delivery_order.dm_pickup_date = dm_delivery_option.get("pickup_date")

            delivery_order.dm_buy_price = dm_delivery_option.get("buy_price")
            delivery_order.dm_sell_price = dm_delivery_option.get("price")
            
            delivery_order.dm_method_id = dm_delivery_option.get("method_id")
            delivery_order.dm_check_id = dm_delivery_option.get("check_id")
            delivery_order.dm_shipment_url = f"https://engine.delmatch.eu/shipment/view/{dm_delivery_option.get('shipment_id')}"
            delivery_order.delivery_option_selected = True  
        except Exception as e:
            print("__________________________________\n\n\n\n")
            print(e)
            print("__________________________________\n\n\n\n")




     

