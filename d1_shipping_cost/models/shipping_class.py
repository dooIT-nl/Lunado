import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class D1ShippingClass(models.Model):
    """Transportklasse (TK1, TK2, TK3, ...).

    Beheerders kunnen klassen aanmaken en beheren. De code wordt gebruikt
    in de berekeningslogica om te bepalen welke flow (bundel, doos, display)
    moet worden gevolgd.
    """

    _name = "d1.shipping.class"
    _description = "D1 Shipping Class"
    _order = "sequence, code"

    name = fields.Char(
        string="Name",
        required=True,
        help="Display name of the shipping class, e.g. 'TK1 — Bundles'.",
    )
    code = fields.Char(
        string="Code",
        required=True,
        help="Technical code, e.g. 'TK1', 'TK2', 'TK3'. Used in calculation logic.",
    )
    description = fields.Text(
        string="Description",
        help="Explanation of the shipping class.",
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
    )

    _sql_constraints = [
        ("code_unique", "unique(code)", "The shipping class code must be unique."),
    ]
