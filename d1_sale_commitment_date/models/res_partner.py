import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    d1_delivery_cutoff_hour = fields.Float(
        string="Delivery Cutoff Time",
        help="Cutoff time for the computed delivery date. If the computed "
        "delivery moment falls at or after this time, the delivery moves to "
        "the next working day. Leave 0:00 to use the system default "
        "(system parameter d1_sale_commitment_date.default_cutoff_hour).",
    )
