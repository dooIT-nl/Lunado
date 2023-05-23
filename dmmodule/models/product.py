from odoo import api, fields, models
import traceback
from .deliverymatch_exception import DeliveryMatchException


class Product(models.Model):
    _inherit = "product.template"

    dm_length = fields.Integer(string='Length (CM)', required=True, default=10)
    dm_width = fields.Integer(string='Width (CM)', required=True, default=10)
    dm_height = fields.Integer(string='Height (CM)', required=True, default=10)
    dm_sku = fields.Char(string="SKU", required=True)
    dm_hscode = fields.Char(string="HSCODE", required=False)
    dm_country_origin = fields.Char(string="Country of Origin", required=False)
    dm_is_fragile = fields.Boolean(string="Fragile")
    dm_is_dangerous = fields.Boolean(string="Dangerous")


class DmProduct:
    def __init__(self, content, description, weight, length, width, height, barcode, warehouse_id, value, stock, quantity,  sku, is_fragile=False, is_dangerous=False, hscode=None, country_origin=None):
        
        if(country_origin == False):
            country_origin = ""
        
        if(hscode == False):
            hscode = ""
            
        if(sku == False):
            sku = ""
        
        
        self.content = content
        self.description = description
        self.weight = weight
        self.length = length
        self.width = width
        self.height = height
        self.is_fragile = is_fragile
        self.is_dangerous = is_dangerous
        self.sku = sku
        self.hscode = hscode
        self.barcode = barcode
        self.warehouse_id = warehouse_id
        self.value = value
        self.stock = stock
        self.country_origin = country_origin
        self.quantity = quantity

        for attribute, value in vars().items():
            if not value and attribute == "warehouse_id":
                self.warehouse_id = 1
                # raise DeliveryMatchException("Warehouse ID missing while fetching products.")

            if not value and attribute not in ["is_fragile", "is_dangerous", "hscode", "country_origin", "stock", "warehouse_id"]:                    
                raise DeliveryMatchException(f"{attribute} is missing. In {content}.") 



class DmProducts:
    def __init__(self):
        self.products: list[DmProduct] = []

    def add_product(self, product: DmProduct):
        self.products.append(product)

    def remove_product(self, product: DmProduct):
        self.products.remove(product)

    def get_products(self) -> list:
        return self.products

    def has_fragile_products(self) -> bool:
        for product in self.products:
            if product.is_fragile:
                return True
        return False

    def has_dangerous_products(self) -> bool:
        for product in self.products:
            if product.is_dangerous:
                return True
        return False

    def total_price_incuding_vat(self) -> float:
        total_price = 0
        for product in self.products:
            total_price += product.value * product.quantity
        return total_price
    
    def total_price_excluding_vat(self) -> float:
        pass

    def total_weight(self) -> float:
        total_weight = 0
        for product in self.products:
            total_weight += product.weight * product.quantity

        return total_weight

    def get_api_format(self, return_tuple=True):
        formatted_products = []

        for product in self.products:
            formatted_product = {
                "weight": product.weight,
                "length": product.length,
                "width": product.width,
                "height": product.height,
                "stock": product.stock,
                "value": product.value,
                "warehouse": product.warehouse_id,
                "quantity": product.quantity,
                "description": product.description,
                "content": product.content,
                "SKU": product.sku,
                "EAN": product.barcode,
                "hsCode": product.hscode,
                "countryOfOrigin": product.country_origin,
            }
            formatted_products.append(formatted_product)

        if(return_tuple):
            return tuple(formatted_products)

        return formatted_products

            
    







            
    # def has_product_in_stock(self, quantity, stock_location_id) -> bool:
    #     self._logger.info("Checking if product is in stock...")

    #     try:
    #         stock_product = self.odoo_env.env['stock.quant'].search([('product_tmpl_id.id', '=', self.id), ('location_id', '=', stock_location_id)])

    #         if stock_product.available_quantity < quantity:
    #             return False

    #         if not stock_product.available_quantity:
    #             return False

    #         return True
    #     except Exception as e:
    #         tb = traceback.format_exc()
    #         self._logger.error(f"{e} \n{tb}")
    #         raise Exception("Failed to check product availability in stock.")
        

    # def has_product_in_stock(self, product_id, quantity, stock_location_id) -> bool:
    #     stock_product = self.odoo_env.env['stock.quant'].search(
    #         [('product_id.id', '=', product_id), ('location_id', '=', stock_location_id)])

    #     if stock_product.available_quantity < quantity:
    #         return False

    #     if not stock_product.available_quantity:
    #         return False

    #     return True


        
    