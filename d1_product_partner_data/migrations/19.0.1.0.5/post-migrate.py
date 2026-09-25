"""Herstelmigratie: verwijder de handmatige Studio-Handling-modellen.

De oude Handling-matrix (x_handling + x_handling_line_b0f2a) is functioneel
vervangen door d1_handling_cost; de data is daar al gemigreerd. Besluit
25-09-2026: de handmatige verwijderstap na verificatie vervalt — deze
migratie ruimt de modellen (met velden, views en tabellen) automatisch op.
Idempotent: op databases zonder deze modellen gebeurt niets.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Verwijder de vervangen Handling-modellen."""
    from odoo.addons.d1_product_partner_data import hooks

    env = api.Environment(cr, SUPERUSER_ID, {})
    hooks._remove_handling_models(env)
    _logger.info("d1_product_partner_data: handling model cleanup finished")
