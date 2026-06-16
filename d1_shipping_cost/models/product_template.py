import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    d1_shipping_class_id = fields.Many2one(
        comodel_name="d1.shipping.class",
        string="Transportklasse",
        help="Transportklasse voor berekening van verzendkosten. "
             "TK1 = bundels (lange producten), TK2 = dozen (op gewicht), "
             "TK3 = dozen (displays/volumineus).",
    )
    d1_length_cm = fields.Float(
        string="Lengte (cm)",
        help="Productlengte in centimeters, gebruikt voor transportkostenberekening.",
    )
    d1_width_cm = fields.Float(
        string="Breedte (cm)",
        help="Productbreedte in centimeters, gebruikt voor transportkostenberekening.",
    )
    d1_height_cm = fields.Float(
        string="Hoogte (cm)",
        help="Producthoogte in centimeters, gebruikt voor transportkostenberekening.",
    )
