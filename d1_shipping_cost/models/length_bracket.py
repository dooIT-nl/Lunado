import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class D1ShippingLengthBracket(models.Model):
    """Configureerbare lengteklasse voor transporttarieven.

    Elk record definieert een bereik in centimeters (van/t.m.).
    De TK1-berekeningslogica zoekt de juiste lengteklasse op basis van
    de maximale productlengte in de order.
    """

    _name = "d1.shipping.length.bracket"
    _description = "D1 Shipping Length Bracket"
    _order = "length_from_cm, length_to_cm"

    name = fields.Char(
        string="Name",
        required=True,
        help="Display name, e.g. '< 1.65 m' or '165 – 214 cm'.",
    )
    length_from_cm = fields.Float(
        string="Length from (cm)",
        required=True,
        default=0.0,
        help="Lower bound of the range (inclusive), in centimeters.",
    )
    length_to_cm = fields.Float(
        string="Length to (cm)",
        required=True,
        default=0.0,
        help="Upper bound of the range (inclusive), in centimeters. "
             "Use 0 for open end (no upper bound).",
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
    )

    @api.constrains("length_from_cm", "length_to_cm")
    def _check_length_range(self):
        """Validate that length_from <= length_to (when length_to > 0)."""
        for rec in self:
            if rec.length_to_cm > 0 and rec.length_from_cm > rec.length_to_cm:
                raise ValidationError(
                    _("'Length from' (%.0f cm) cannot be greater than 'Length to' (%.0f cm).")
                    % (rec.length_from_cm, rec.length_to_cm)
                )
