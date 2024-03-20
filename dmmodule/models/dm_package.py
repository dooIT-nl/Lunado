import logging

from odoo import models, fields
from odoo.exceptions import UserError


class DmPackage(models.Model):
    _name = "dm.package"
    _description = "DeliveryMatch Package"
    _logger = logging.getLogger("dm.package")

    height = fields.Float(string="Height (CM)", required=True)
    width = fields.Float(string="Width (CM)", required=True)
    length = fields.Float(string="Length (CM)", required=True)
    weight = fields.Float(string="Weight (KG)", required=True)

    description = fields.Char(string="Description", required=True)
    type = fields.Char(string="Type", required=True)

    sale_order_id = fields.Many2one("sale.order", "Sale Order ID")
    stock_picking_id = fields.Many2one("stock.picking", "Stock Picking Id")

    def to_api_format(self):
        return {
            "description": self.description,
            "type": self.type,
            "height": self.height,
            "width": self.width,
            "length": self.length,
            "weight": self.weight
        }


