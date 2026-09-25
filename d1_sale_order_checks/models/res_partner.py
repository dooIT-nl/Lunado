import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    d1_rel_type = fields.Selection(
        selection=[
            ("prospect", "Prospect"),
            ("customer", "Customer"),
        ],
        string="Relation Type",
        help="Sale orders cannot be created for partners of type Prospect.",
    )
    d1_credit_insurance = fields.Selection(
        selection=[
            ("insured_own", "Insured, own assessment"),
            ("insured_insurer", "Insured, insurer assessment"),
            ("not_insured", "Not insured"),
        ],
        string="Credit Insurance",
    )
    # Bewust Float i.p.v. Monetary: res.partner heeft geen currency-veld en
    # het oorspronkelijke Studio-veld was eveneens Float (bedrag in
    # bedrijfsvaluta).
    d1_insured_amount = fields.Float(
        string="Insured Amount",
        help="Amount covered by the credit insurance (company currency).",
    )
