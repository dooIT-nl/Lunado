from odoo import models, fields
# comment
class ProductProduct(models.Model):
    _inherit = "product.product"

    x_studio_use_qty = fields.Boolean(store=True)
    x_studio_use_length = fields.Boolean(store=True)
