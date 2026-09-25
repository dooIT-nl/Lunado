import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    d1_framecalculator_url = fields.Char(
        string="Framecalculator URL",
        config_parameter="d1_framecalculator.url",
        help="Base URL of the external frame calculator, without "
        "parameters, e.g. https://lunado-framecalculator.example.com",
    )
    d1_framecalculator_api_key = fields.Char(
        string="Framecalculator API Key",
        config_parameter="d1_framecalculator.api_key",
        help="Plain (not URL-encoded) API key for the frame calculator; "
        "it is encoded automatically when the URL is built.",
    )
