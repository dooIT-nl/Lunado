import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    d1_default_warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse",
        string="Default Warehouse",
        help="Warehouse this product is normally shipped from. Required for "
        "goods on combi orders: lines whose default warehouse differs from "
        "the order warehouse get the combi route of the order warehouse.",
    )
