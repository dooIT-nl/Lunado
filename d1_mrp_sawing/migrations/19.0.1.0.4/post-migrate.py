"""Herstelmigratie: draai de Studio-opschoning opnieuw.

De oorspronkelijke installatie op staging liet enkele x_studio-velden staan
omdat Studio-views ernaar verwezen in attributen/xpath-expressies. De
opschoonlogica in hooks.py is robuuster gemaakt; deze migratie voert hem bij
de module-update nogmaals uit (idempotent).
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Voer de (robuustere) Studio-opschoning nogmaals uit."""
    from odoo.addons.d1_mrp_sawing import hooks

    env = api.Environment(cr, SUPERUSER_ID, {})
    hooks._remove_replaced_automations(env)
    hooks._remove_replaced_fields(env)
    _logger.info("d1_mrp_sawing: studio cleanup re-run finished")
