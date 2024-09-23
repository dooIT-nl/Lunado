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
    is_fragile_package = fields.Boolean(string="Is fragile package")

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

    @staticmethod
    def convert_size_to_cm(packages):
        for package in packages:
            package['height'] = package['height'] / 10
            package['width'] = package['width'] / 10
            package['length'] = package['length'] / 10

        return packages

