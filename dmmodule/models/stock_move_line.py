from odoo import fields, models, api


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'
    product_dm_hscode = fields.Char(string="HS-CODE", related="product_id.dm_hscode", copy=False, readonly=False)