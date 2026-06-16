import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # TODO (open punt): alle drempelwaarden nog vast te stellen met business
    d1_tk1_max_bundels = fields.Integer(
        string="TK1 max bundels",
        help="Maximaal aantal bundels vóór palletberekening (handmatig). "
             "Waarde nog vast te stellen.",
        config_parameter="d1_shipping.tk1_max_bundels",
        default=99999,
    )
    d1_tk2_max_gewicht_kg = fields.Float(
        string="TK2 max gewicht (kg)",
        help="Maximaal totaalgewicht TK2 vóór palletberekening. "
             "Waarde nog vast te stellen.",
        config_parameter="d1_shipping.tk2_max_gewicht_kg",
        default=99999.0,
    )
    d1_tk3_max_gewicht_kg = fields.Float(
        string="TK3 max gewicht (kg)",
        help="Maximaal totaalgewicht TK3 vóór palletberekening. "
             "Waarde nog vast te stellen.",
        config_parameter="d1_shipping.tk3_max_gewicht_kg",
        default=99999.0,
    )
    # TODO (open punt): bundel-/doosafmetingen (15×15 cm, 20 kg) zijn aannames — bevestigen
    d1_bundle_width_cm = fields.Float(
        string="Bundelbreedte (cm)",
        config_parameter="d1_shipping.bundle_width_cm",
        default=15.0,
    )
    d1_bundle_height_cm = fields.Float(
        string="Bundelhoogte (cm)",
        config_parameter="d1_shipping.bundle_height_cm",
        default=15.0,
    )
    d1_bundle_max_weight_kg = fields.Float(
        string="Max gewicht bundel (kg)",
        config_parameter="d1_shipping.bundle_max_weight_kg",
        default=20.0,
    )
    d1_box_max_weight_kg = fields.Float(
        string="Max gewicht doos (kg)",
        config_parameter="d1_shipping.box_max_weight_kg",
        default=20.0,
    )
