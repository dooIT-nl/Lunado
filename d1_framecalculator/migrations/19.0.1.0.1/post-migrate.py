"""Vertaal de verkorte instellingen-labels op reeds geinstalleerde
databases (verse installaties krijgen ze via de po-bestanden)."""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Zet de vertalingen van de nieuwe view-labels (URL / API Key)."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    view = env.ref(
        "d1_framecalculator.d1_res_config_settings_view_form",
        raise_if_not_found=False,
    )
    if not view:
        return
    view.update_field_translations("arch_db", {
        "nl_NL": {"API Key": "API-key"},
        "de_DE": {"API Key": "API-Schluessel"},
    })
    _logger.info("d1_framecalculator: settings label translations applied")
