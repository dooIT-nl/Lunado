from odoo import fields, models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    # x_studio_hoeveelheid = fields.Integer(string="Hoeveelheid")
    product_dm_hscode = fields.Char(string="HS-CODE", related="product_id.dm_hscode", readonly=True)
    show_column_hscode = fields.Boolean(string="Show column HS CODE", related="picking_id.show_product_hscode", readonly=True)
