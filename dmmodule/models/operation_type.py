from odoo import api, fields, models, _
from odoo.exceptions import UserError
import traceback
import logging

class OperationType(models.Model):
    _inherit = "stock.picking.type"
    dm_is_inbound = fields.Boolean(default=False, string="DeliveryMatch - inbound")
    dm_warehouse_number = fields.Selection(string='Warehouse nr DeliveryMatch', related='warehouse_id.warehouse_options')

