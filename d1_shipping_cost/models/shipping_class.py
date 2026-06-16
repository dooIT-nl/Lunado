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
        string="Naam",
        required=True,
        help="Weergavenaam van de transportklasse, bv. 'TK1 — Bundels'.",
    )
    code = fields.Char(
        string="Code",
        required=True,
        help="Technische code, bv. 'tk1', 'tk2', 'tk3'. "
             "Wordt gebruikt in de berekeningslogica.",
    )
    description = fields.Text(
        string="Omschrijving",
        help="Toelichting op de transportklasse.",
    )
    sequence = fields.Integer(
        string="Volgorde",
        default=10,
    )

    _sql_constraints = [
        ("code_unique", "unique(code)", "De code van een transportklasse moet uniek zijn."),
    ]
