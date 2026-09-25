"""Tijdelijke aliassen van oude Studio-veldnamen (deprecated).

Bijzonderheden:
* x_studio_rel_type en x_studio_kredietverzekering hadden in Studio de
  Nederlandse labels als waarde; de aliassen vertalen die van/naar de
  nieuwe technische keys zodat bestaande koppelingen dezelfde waarden
  blijven lezen en schrijven.
* x_studio_handling verwijst nu naar d1.handling-records: de ids wijken af
  van de oude x_handling-ids (gemigreerde records).
"""
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

REL_TYPE_MAP = {"prospect": "Prospect", "customer": "Klant"}
REL_TYPE_INV = {v: k for k, v in REL_TYPE_MAP.items()}
INSURANCE_MAP = {
    "insured_own": "Verzekerd, eigen beoordeling",
    "insured_insurer": "Verzekerd, beoordeling verzekeraar",
    "not_insured": "Niet verzekerd",
}
INSURANCE_INV = {v: k for k, v in INSURANCE_MAP.items()}


class ResPartner(models.Model):
    _inherit = "res.partner"

    x_studio_dropshipment = fields.Boolean(
        related="d1_dropshipment", readonly=False,
        string="Dropshipment (compat)")
    x_studio_verzekerd_bedrag = fields.Float(
        related="d1_insured_amount", readonly=False,
        string="Insured Amount (compat)")
    x_studio_incoterm_id = fields.Many2one(
        related="d1_incoterm_id", readonly=False,
        string="Incoterm (compat)")
    x_studio_type_levering = fields.Many2one(
        related="d1_delivery_picking_type_id", readonly=False,
        string="Delivery Type (compat)")
    x_studio_handling = fields.Many2one(
        related="d1_handling_id", readonly=False,
        string="Handling (compat)")
    x_studio_coc = fields.Char(
        related="company_registry", readonly=False, string="CoC (compat)")
    x_studio_rel_type = fields.Char(
        compute="_compute_x_studio_rel_type",
        inverse="_inverse_x_studio_rel_type",
        string="Relation Type (compat)",
        help="Compat-alias met de oude Studio-waarden 'Prospect'/'Klant'.")
    x_studio_kredietverzekering = fields.Char(
        compute="_compute_x_studio_kredietverzekering",
        inverse="_inverse_x_studio_kredietverzekering",
        string="Credit Insurance (compat)",
        help="Compat-alias met de oude Nederlandse Studio-waarden.")

    @api.depends("d1_rel_type")
    def _compute_x_studio_rel_type(self):
        """Geef de oude Studio-waarde ('Prospect'/'Klant') terug."""
        for partner in self:
            partner.x_studio_rel_type = REL_TYPE_MAP.get(
                partner.d1_rel_type, False)

    def _inverse_x_studio_rel_type(self):
        """Vertaal de oude Studio-waarde naar de nieuwe selectiekey."""
        for partner in self:
            partner.d1_rel_type = REL_TYPE_INV.get(
                partner.x_studio_rel_type or "", False)

    @api.depends("d1_credit_insurance")
    def _compute_x_studio_kredietverzekering(self):
        """Geef de oude Nederlandse Studio-waarde terug."""
        for partner in self:
            partner.x_studio_kredietverzekering = INSURANCE_MAP.get(
                partner.d1_credit_insurance, False)

    def _inverse_x_studio_kredietverzekering(self):
        """Vertaal de oude Studio-waarde naar de nieuwe selectiekey."""
        for partner in self:
            partner.d1_credit_insurance = INSURANCE_INV.get(
                partner.x_studio_kredietverzekering or "", False)
