import logging

from odoo import fields, models
from odoo.exceptions import UserError


class ProductPackaging(models.Model):
    _inherit = "product.packaging"
    _logger = logging.getLogger("product.packaging")

    min_qty = fields.Float(string="Minimum Contained Quantity")
