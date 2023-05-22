from odoo import api, fields, models, _
from odoo.exceptions import UserError
import traceback
import logging

class CustomerPartners(models.Model):
    _inherit = "res.partner"
    
    is_franco_order = fields.Boolean(string="DeliveryMatch - FRANCO", default=False)

