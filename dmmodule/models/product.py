from odoo import fields, models
from .deliverymatch_exception import DeliveryMatchException
from .helper import Helper

class Product(models.Model):
    _inherit = "product.template"

    dm_length = fields.Integer(string='Length (CM)', required=True, default=10)
    dm_width = fields.Integer(string='Width (CM)', required=True, default=10)
    dm_height = fields.Integer(string='Height (CM)', required=True, default=10)
    dm_sku = fields.Char(string="SKU", required=False)
    dm_hscode = fields.Char(string="HSCODE", required=False)
    dm_country_origin = fields.Char(string="DM Country Origin", required=False)
    dm_is_fragile = fields.Boolean(string="Fragile")
    dm_is_dangerous = fields.Boolean(string="Dangerous")
    dm_send_lot_code = fields.Boolean(string="WSL lotcode")
    dm_combinable_in_package = fields.Boolean(string="Combinable in packages")
    dm_lithium_battery_weight = fields.Float(string="Lithium battery weight (KG)", default=None)

    un_number = fields.Char(string="UN Number")
    dg_packing_instruction = fields.Char(string="Packaging instruction")

    # default in cm3
    def get_dm_volume(self, convert_to_m3:bool = False) -> float:
        volume = self.dm_length * self.dm_width * self.dm_height

        if convert_to_m3: volume = volume / 1_000_000

        return volume

class DmProduct:
    def __init__(self, content, description, weight, length, width, height, warehouse_id, value, stock, quantity, sku=None, barcode=None, is_fragile=False, is_dangerous=False, hscode=None, country_origin=None, custom1=None, dangerous_goods=None, lithium_battery_weight=None):
        
        if not country_origin:
            country_origin = ""
        
        if not hscode:
            hscode = ""
            
        if not sku:
            sku = ""
            
        if not custom1:
            custom1 = ""
        
        
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
        self.custom1 = custom1
        self.dangerous_goods = dangerous_goods
        self.lithium_battery_weight = lithium_battery_weight

        for attribute, value in vars().items():
            if not value and attribute == "warehouse_id":
                self.warehouse_id = 1
                # raise DeliveryMatchException("Warehouse ID missing while fetching products.")

            if not value and attribute not in ["is_fragile", "is_dangerous", "hscode", "country_origin", "stock", "warehouse_id", "custom1", "barcode", "sku", "dangerous_goods", "lithium_battery_weight"]:
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

    def total_lithium_battery_weight(self):
        total = 0
        for product in self.products:
            if product.is_dangerous:
                total += product.lithium_battery_weight * product.quantity

        return total

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
                "hsCode": product.hscode,
                "countryOfOrigin": product.country_origin,
                "custom1": product.custom1
            }

            if product.dangerous_goods is not None:
                formatted_product["dangerousGoods"] = product.dangerous_goods

            if not Helper.is_empty(product.sku):
                formatted_product['SKU'] = product.sku

            if not Helper.is_empty(product.barcode):
                formatted_product['EAN'] = product.barcode

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


        
    