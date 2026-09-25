import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    d1_shipping_class_id = fields.Many2one(
        comodel_name="d1.shipping.class",
        string="Shipping Class",
        help="Shipping class for transport cost calculation. "
             "TK1 = bundles (long products), TK2 = boxes (by weight), "
             "TK3 = boxes (displays/voluminous).",
    )
    d1_length_cm = fields.Float(
        string="Length (cm)",
        help="Product length in centimeters, used for transport cost calculation.",
    )
    d1_width_cm = fields.Float(
        string="Width (cm)",
        help="Product width in centimeters, used for transport cost calculation.",
    )
    d1_height_cm = fields.Float(
        string="Height (cm)",
        help="Product height in centimeters, used for transport cost calculation.",
    )
    d1_use_qty = fields.Boolean(
        string="Use Quantity",
        copy=True,
        help="If checked, the order line quantity is calculated as "
             "d1_qty × d1_length instead of being entered manually.",
    )
    d1_use_length = fields.Boolean(
        string="Use Length",
        copy=True,
        help="If checked, the user can enter a custom length on the "
             "order line. Otherwise the product length is used.",
    )
