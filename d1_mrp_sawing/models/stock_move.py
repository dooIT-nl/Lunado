import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    d1_qty = fields.Float(
        string="Sawing Quantity",
        related="sale_line_id.d1_qty",
    )
    d1_length = fields.Float(
        string="Length",
        related="sale_line_id.d1_length",
    )
    d1_production_time = fields.Float(
        string="Production Time Finished Product",
        related="production_id.d1_production_time",
    )
