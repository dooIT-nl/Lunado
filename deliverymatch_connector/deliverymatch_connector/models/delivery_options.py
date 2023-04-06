from odoo import models, fields

class DeliveryOptions(models.Model):
    _name = "delivery.options"
    _description = "handles the delivery options"
    carrier_name = fields.Char(string="Carrier name")
    