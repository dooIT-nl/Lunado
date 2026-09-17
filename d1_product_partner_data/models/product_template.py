import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    d1_abc_code = fields.Selection(
        selection=[
            ("04", "04"),
            ("05", "05"),
            ("06", "06"),
            ("07", "07"),
        ],
        string="ABC Code",
    )
    d1_courant = fields.Boolean(
        string="Courant",
        help="Fast-moving product.",
    )
    d1_available = fields.Boolean(
        string="Available",
        compute="_compute_d1_available",
        store=True,
        help="On-hand quantity is positive; always false for products with "
        "a subcontracting bill of materials.",
    )
    d1_package_count = fields.Integer(
        string="Packaging Count",
        compute="_compute_d1_package_count",
        store=True,
        help="Number of packaging units of measure defined on the product "
        "(Odoo 19: packagings are extra UoMs).",
    )
    d1_cost_calc = fields.Monetary(
        string="Calculated Cost",
        currency_field="cost_currency_id",
        help="Calculated cost price, filled by the frame calculator / "
        "external calculation.",
    )

    @api.depends("qty_available", "bom_ids.type")
    def _compute_d1_available(self):
        """Beschikbaar = fysieke voorraad > 0, behalve voor producten met een
        subcontract-stuklijst (altijd niet-beschikbaar).

        Herbouwd 'zoals bedoeld' (besluit 17-09-2026): de Studio-versie liet
        producten zonder voorraad en zonder stuklijst hun oude waarde
        behouden. Kanttekening (gold ook voor de Studio-versie): het veld is
        opgeslagen maar qty_available is dat niet — de waarde wordt ververst
        bij wijzigingen aan het product/de stuklijst en bij herberekening,
        niet bij elke losse voorraadmutatie.
        """
        for template in self:
            if any(bom.type == "subcontract" for bom in template.bom_ids):
                template.d1_available = False
            else:
                template.d1_available = template.qty_available > 0

    @api.depends("uom_ids")
    def _compute_d1_package_count(self):
        """Aantal verpakkings-UoM's op het product (Odoo 19-equivalent van
        het aantal productverpakkingen)."""
        for template in self:
            template.d1_package_count = len(template.uom_ids)
