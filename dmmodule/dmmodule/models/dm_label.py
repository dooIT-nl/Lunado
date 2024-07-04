from odoo import models, fields


class DmLabel(models.Model):
    _name = "dm.label"
    _description = "DeliveryMatch Package"
    stock_picking_id = fields.Integer("Stock Picking Id")

    label_url = fields.Char(string="Label URL")
    tracking_url = fields.Char(string="Tracking URL")
    barcode = fields.Char(string="Barcode")

    height = fields.Float(string="Height (CM)")
    width = fields.Float(string="Width (CM)")
    length = fields.Float(string="Length (CM)")
    weight = fields.Float(string="Weight (KG)")

    description = fields.Char(string="Description")
    type = fields.Char(string="Type")