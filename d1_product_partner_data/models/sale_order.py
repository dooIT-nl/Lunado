import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    d1_delivery_note_url = fields.Char(
        string="Packing Slip URL",
        copy=False,
        help="Link to the external packing slip, filled by the integration.",
    )
