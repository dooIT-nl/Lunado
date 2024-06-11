import logging

from odoo import fields, models, api

class ProductPackaging(models.Model):
    _inherit = "product.packaging"
    _logger = logging.getLogger("product.packaging")

    min_qty = fields.Float(string="Minimum Contained Quantity")