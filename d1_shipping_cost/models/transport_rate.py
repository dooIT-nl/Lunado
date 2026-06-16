import logging
import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class D1ShippingRate(models.Model):
    """Tariefstaffel voor transportkosten per klasse, land en eenheidsstaffel.

    Beheerders onderhouden deze tabel via Verkoop > Configuratie > Transporttarieven.
    De berekeningslogica op sale.order zoekt hier het juiste tarief op.

    Adresfiltering werkt identiek aan delivery.carrier:
    - country_ids: als ingevuld, moet het land van het afleveradres erin staan.
    - state_ids: als ingevuld, moet de provincie erin staan.
    - zip_prefix_ids: als ingevuld, moet de postcode beginnen met een van de
      prefixen (reguliere expressies ondersteund).
    Als alle drie leeg zijn, geldt het tarief voor alle adressen.
    """

    _name = "d1.shipping.rate"
    _description = "D1 Shipping Rate"
    _order = "shipping_class_id, length_bracket_id, qty_from"

    name = fields.Char(
        string="Naam",
        required=True,
    )
    shipping_class_id = fields.Many2one(
        comodel_name="d1.shipping.class",
        string="Transportklasse",
        required=True,
    )

    # --- Address filtering (same pattern as delivery.carrier) ---
    country_ids = fields.Many2many(
        comodel_name="res.country",
        relation="d1_shipping_rate_country_rel",
        column1="rate_id",
        column2="country_id",
        string="Landen",
        help="Landen waarvoor dit tarief geldt. Laat leeg voor alle landen.",
    )
    state_ids = fields.Many2many(
        comodel_name="res.country.state",
        relation="d1_shipping_rate_state_rel",
        column1="rate_id",
        column2="state_id",
        string="Provincies",
        help="Provincies/staten waarvoor dit tarief geldt. Laat leeg voor alle provincies.",
    )
    zip_prefix_ids = fields.Many2many(
        comodel_name="d1.shipping.zip.prefix",
        relation="d1_shipping_rate_zip_prefix_rel",
        column1="rate_id",
        column2="zip_prefix_id",
        string="Postcode-prefixen",
        help="Postcode-prefixen waarvoor dit tarief geldt. "
             "Reguliere expressies worden ondersteund, bv. '$' aan het einde "
             "matcht de exacte postcode (bijv. '100$' matcht alleen '100'). "
             "Laat leeg voor alle postcodes.",
    )

    length_bracket_id = fields.Many2one(
        comodel_name="d1.shipping.length.bracket",
        string="Lengteklasse",
        help="Alleen van toepassing voor TK1. Laat leeg voor TK2/TK3.",
    )
    unit_type = fields.Selection(
        selection=[
            ("bundle", "Bundels"),
            ("box", "Dozen"),
        ],
        string="Eenheidstype",
        required=True,
        help="TK1 = bundels; TK2/TK3 = dozen.",
    )
    qty_from = fields.Integer(
        string="Aantal vanaf",
        required=True,
        help="Ondergrens van de staffel (inclusief).",
    )
    qty_to = fields.Integer(
        string="Aantal t/m",
        required=True,
        help="Bovengrens van de staffel (inclusief). Gebruik 0 of een groot getal voor open einde.",
    )
    price = fields.Float(
        string="Tarief",
        required=True,
        digits="Product Price",
        help="Tarief voor deze staffel. Wordt als totaalbedrag voor de staffelrange toegepast.",
    )

    @api.constrains("qty_from", "qty_to")
    def _check_qty_range(self):
        """Validate that qty_from <= qty_to (when qty_to > 0)."""
        for rec in self:
            if rec.qty_to > 0 and rec.qty_from > rec.qty_to:
                raise ValidationError(
                    _("'Aantal vanaf' (%s) mag niet groter zijn dan 'Aantal t/m' (%s).")
                    % (rec.qty_from, rec.qty_to)
                )

    def _match_address(self, partner):
        """Check if this rate matches the given partner's address.

        Same logic as delivery.carrier._match_address():
        - country_ids: partner's country must be in the list (if set).
        - state_ids: partner's state must be in the list (if set).
        - zip_prefix_ids: partner's zip must match one of the prefixes (if set).
        All empty = matches any address.

        Returns True if the address matches, False otherwise.
        """
        self.ensure_one()
        if self.country_ids and partner.country_id not in self.country_ids:
            return False
        if self.state_ids and partner.state_id not in self.state_ids:
            return False
        if self.zip_prefix_ids:
            regex = re.compile(
                "|".join("^" + zp for zp in self.zip_prefix_ids.mapped("name"))
            )
            if not partner.zip or not re.match(regex, partner.zip.upper()):
                return False
        return True
