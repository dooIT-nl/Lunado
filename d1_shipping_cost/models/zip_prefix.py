import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class D1ShippingZipPrefix(models.Model):
    """Postcode-prefix voor adresfiltering op transporttarieven.

    Ondersteunt reguliere expressies, bv. '100$' matcht alleen '100'
    en niet '1000'. Prefixen worden automatisch naar hoofdletters omgezet.

    Identieke opzet als delivery.zip.prefix in de delivery-module.
    """

    _name = "d1.shipping.zip.prefix"
    _description = "D1 Shipping Zip Prefix"
    _order = "name, id"

    name = fields.Char(
        string="Prefix",
        required=True,
        help="Postcode-prefix. Reguliere expressies worden ondersteund, "
             "bv. '100$' matcht alleen exact '100'. Wordt automatisch "
             "naar hoofdletters omgezet.",
    )

    _sql_constraints = [
        ("name_unique", "unique(name)", "Dit prefix bestaat al."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        """Ensure zip prefixes are always stored in uppercase."""
        for vals in vals_list:
            if vals.get("name"):
                vals["name"] = vals["name"].upper()
        return super().create(vals_list)

    def write(self, vals):
        """Ensure zip prefixes are always stored in uppercase."""
        if "name" in vals and vals["name"]:
            vals["name"] = vals["name"].upper()
        return super().write(vals)
