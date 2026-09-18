"""Herstelmigratie: draai de Studio-eindschoonmaak opnieuw.

De oorspronkelijke installatie op staging liet x_studio_available en
x_studio_kostprijs_calc staan (view-verwijzingen in attributen) en
x_studio_handling stond nog in geen enkele opruimlijst. De opschoonlogica in
hooks.py is robuuster gemaakt; deze migratie voert hem bij de module-update
nogmaals uit (idempotent).
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Voer de (robuustere) Studio-eindschoonmaak nogmaals uit."""
    from odoo.addons.d1_product_partner_data import hooks

    env = api.Environment(cr, SUPERUSER_ID, {})
    hooks._remove_replaced_automations(env)
    hooks._remove_replaced_fields(env)
    hooks._deactivate_remaining_studio_views(env)
    _logger.info("d1_product_partner_data: studio cleanup re-run finished")
