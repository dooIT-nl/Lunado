import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    d1_dropshipment = fields.Boolean(
        string="Dropshipment",
        help="New sale orders for this customer are flagged as dropshipment "
        "by default.",
    )
