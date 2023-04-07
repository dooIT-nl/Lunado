from odoo import api, fields, models

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
            

        
    