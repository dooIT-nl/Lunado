from odoo import fields, models
from odoo.exceptions import UserError
import traceback
import logging

class CustomerPartners(models.Model):
    _inherit = "res.partner"
    
    is_franco_order = fields.Boolean(string="DeliveryMatch franco", default=False)

