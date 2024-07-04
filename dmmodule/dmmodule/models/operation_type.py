from odoo import fields, models, _

class OperationType(models.Model):
    _inherit = "stock.picking.type"
    dm_warehouse_number = fields.Selection(string='Warehouse nr DeliveryMatch', related='warehouse_id.warehouse_options')

