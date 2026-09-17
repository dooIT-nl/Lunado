import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ProductCategory(models.Model):
    _inherit = "product.category"

    d1_extra_service_product_id = fields.Many2one(
        comodel_name="product.template",
        string="Extra Service",
        help="Service product that is automatically added to sale orders "
        "containing products of this category. The service quantity is the "
        "sum of the sawing quantities of those lines.",
    )
