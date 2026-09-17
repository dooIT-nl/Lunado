import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    d1_no_partner_delivery_default = fields.Boolean(
        string="No Partner Delivery Defaults",
        help="When a purchase order uses this operation type, the vendor's "
        "delivery operation type and incoterm are NOT applied (e.g. for "
        "Dropship orders).",
    )
