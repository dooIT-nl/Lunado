"""Tijdelijke aliassen van oude Studio-veldnamen (deprecated).

Alle velden zijn related naar het vervangende d1_-veld; berekende velden
zijn alleen-lezen. Ook bereikbaar via product.product (template-velden zijn
zichtbaar op de variant), precies zoals de oude Studio-velden.
"""
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    x_studio_use_qty = fields.Boolean(
        related="d1_use_qty", readonly=False, string="Use Quantity (compat)")
    x_studio_use_length = fields.Boolean(
        related="d1_use_length", readonly=False,
        string="Use Length (compat)")
    x_studio_zaagcap_bew = fields.Integer(
        related="d1_saw_capacity", readonly=False,
        string="Saw Capacity (compat)")
    x_studio_zaagtijd_per_bew = fields.Integer(
        related="d1_saw_time", readonly=False, string="Saw Time (compat)")
    x_studio_artikelcode_gezaagd = fields.Many2one(
        related="d1_raw_product_id", readonly=False,
        string="Full-Length Product (compat)")
    x_studio_framecalculator_janee = fields.Boolean(
        related="d1_framecalculator", readonly=False,
        string="Frame Calculator (compat)")
    x_studio_abc_code = fields.Selection(
        related="d1_abc_code", readonly=False, string="ABC Code (compat)")
    x_studio_courant = fields.Boolean(
        related="d1_courant", readonly=False, string="Courant (compat)")
    x_studio_available = fields.Boolean(
        related="d1_available", string="Available (compat)")
    x_studio_aantal_verpakkingen = fields.Integer(
        related="d1_package_count", string="Packaging Count (compat)")
    x_studio_kostprijs_calc = fields.Monetary(
        related="d1_cost_calc", readonly=False,
        currency_field="cost_currency_id",
        string="Calculated Cost (compat)")
    x_studio_default_warehouse_id = fields.Many2one(
        related="d1_default_warehouse_id", readonly=False,
        string="Default Warehouse (compat)")
