"""Tijdelijke aliassen van oude Studio-veldnamen (deprecated)."""
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    x_studio_qty = fields.Float(
        related="d1_qty", readonly=False, string="Sawing Qty (compat)")
    x_studio_length = fields.Float(
        related="d1_length", readonly=False, string="Length (compat)")
    x_studio_use_qty = fields.Boolean(
        related="d1_use_qty", string="Use Quantity (compat)")
    x_studio_use_length = fields.Boolean(
        related="d1_use_length", string="Use Length (compat)")
    x_studio_weight = fields.Float(
        related="d1_weight", string="Weight (compat)")
    x_studio_frame_id = fields.Char(
        related="d1_frame_id", readonly=False, string="Frame ID (compat)")
    x_studio_frame_nr = fields.Char(
        related="d1_frame_nr", string="Frame Number (compat)")
    x_studio_qty_var_name = fields.Char(
        related="d1_qty_var_name", readonly=False,
        string="Qty Var Name (compat)")
