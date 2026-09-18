"""Tijdelijke aliassen van oude Studio-veldnamen (deprecated)."""
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    x_studio_dropshipment = fields.Boolean(
        related="d1_dropshipment", readonly=False,
        string="Dropshipment (compat)")
    x_studio_combi = fields.Boolean(
        related="d1_combi", readonly=False, string="Combi (compat)")
    x_studio_exceed_credit_limit = fields.Boolean(
        related="d1_exceed_credit_limit", readonly=False,
        string="Exceed Credit Limit (compat)")
    x_studio_credit_limit_exceeded = fields.Boolean(
        related="d1_credit_limit_exceeded",
        string="Credit Limit Exceeded (compat)")
    x_studio_url_pakbon = fields.Char(
        related="d1_delivery_note_url", readonly=False,
        string="Packing Slip URL (compat)")
