import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # TODO (open punt): alle drempelwaarden nog vast te stellen met business
    d1_tk1_max_bundels = fields.Integer(
        string="TK1 Max Bundles",
        help="Maximum number of bundles before pallet calculation (manual).",
        config_parameter="d1_shipping.tk1_max_bundels",
        default=99999,
    )
    d1_tk2_max_gewicht_kg = fields.Float(
        string="TK2 Max Weight (kg)",
        help="Maximum total weight TK2 before pallet calculation.",
        config_parameter="d1_shipping.tk2_max_gewicht_kg",
        default=99999.0,
    )
    d1_tk3_max_gewicht_kg = fields.Float(
        string="TK3 Max Weight (kg)",
        help="Maximum total weight TK3 before pallet calculation.",
        config_parameter="d1_shipping.tk3_max_gewicht_kg",
        default=99999.0,
    )
    # TODO (open punt): bundel-/doosafmetingen (15×15 cm, 20 kg) zijn aannames — bevestigen
    d1_bundle_width_cm = fields.Float(
        string="Bundle Width (cm)",
        config_parameter="d1_shipping.bundle_width_cm",
        default=15.0,
    )
    d1_bundle_height_cm = fields.Float(
        string="Bundle Height (cm)",
        config_parameter="d1_shipping.bundle_height_cm",
        default=15.0,
    )
    d1_bundle_max_weight_kg = fields.Float(
        string="Max Bundle Weight (kg)",
        config_parameter="d1_shipping.bundle_max_weight_kg",
        default=20.0,
    )
    d1_box_max_weight_kg = fields.Float(
        string="Max Box Weight (kg)",
        config_parameter="d1_shipping.box_max_weight_kg",
        default=20.0,
    )
