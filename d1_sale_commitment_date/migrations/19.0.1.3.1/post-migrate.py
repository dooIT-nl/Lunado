"""Herstelmigratie voor bevinding CIS20260925.

Op staging is de cutoff-kolom via Studio aan de partnerlijst toegevoegd
zonder float_time-widget, waardoor het veld als kaal getal toonde. De module
levert nu zelf een (optionele) kolom mét tijdnotatie; deze migratie
deactiveert Studio-lijstviews op res.partner die naar het veld verwijzen,
zodat er geen dubbele/foute kolom overblijft.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Deactiveer Studio-lijstviews op res.partner met de cutoff-kolom."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    views = env["ir.ui.view"].search(
        [
            ("model", "=", "res.partner"),
            ("type", "=", "list"),
            ("arch_db", "like", "d1_delivery_cutoff_hour"),
            ("active", "=", True),
        ]
    )
    for view in views:
        xml_id = view.get_external_id().get(view.id) or ""
        if not xml_id.startswith("studio_customization."):
            continue
        view.active = False
        _logger.info(
            "d1_sale_commitment_date: deactivated studio list view '%s' "
            "(cutoff column without float_time widget, CIS20260925)",
            view.name,
        )
