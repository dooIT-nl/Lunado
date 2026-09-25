"""Herstelmigratie: Handling-modelverwijdering, definitieve aanpak.

De veld-voor-veld-aanpak van v1.0.6 blokkeerde op de afhankelijkheden binnen
de matrix-modellen en liet het register vervuild achter, waarna de
view-deactivatie de installatie afbrak ('Field x_active does not exist' —
go-live-rehearsal 25-09-2026). De modellen worden nu in een unlink met de
uninstall-vlag verwijderd (Odoo's eigen cascade); deze migratie voert de
opschoning nogmaals uit en deactiveert resterende Studio-views (idempotent).
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Verwijder de vervangen Handling-modellen (uninstall-vlag-cascade)."""
    from odoo.addons.d1_product_partner_data import hooks

    env = api.Environment(cr, SUPERUSER_ID, {})
    hooks._remove_handling_models(env)
    hooks._deactivate_remaining_studio_views(env)
    _logger.info("d1_product_partner_data: handling model cleanup (v1.0.7) "
                 "finished")
