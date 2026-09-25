"""Herstelmigratie: draai de Handling-modelverwijdering opnieuw.

De eerste poging (v1.0.5) blokkeerde op de afhankelijkheidsketen binnen het
regelmodel: het related-veld x_currency_id hangt op x_handling_id, waardoor
de cascade van ir.model.unlink weigerde. De opschoonlogica verwijdert de
velden nu vooraf in meerdere passes; deze migratie voert hem nogmaals uit
(idempotent — op databases waar de modellen al weg zijn gebeurt niets).
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Verwijder de vervangen Handling-modellen (tweede, robuustere poging)."""
    from odoo.addons.d1_product_partner_data import hooks

    env = api.Environment(cr, SUPERUSER_ID, {})
    hooks._remove_handling_models(env)
    _logger.info("d1_product_partner_data: handling model cleanup re-run "
                 "finished")
