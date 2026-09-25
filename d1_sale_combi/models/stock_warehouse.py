import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    d1_combi_route_id = fields.Many2one(
        comodel_name="stock.route",
        string="Combi Route",
        help="Route applied to combi order lines when the product's default "
        "warehouse differs from this (order) warehouse. Without a combi "
        "route, combi orders for this warehouse are blocked.",
    )
