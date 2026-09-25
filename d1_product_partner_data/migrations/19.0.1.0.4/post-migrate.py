"""Herstelmigratie: verwijder wees-veldrijen van de Studio-conversie.

Na het verwijderen van de handmatige x_studio-velden op product.template en
res.partner bleven de automatisch gedelegeerde velden (_inherits) op
product.product en res.users als 'basisveld'-metadata achter — 35 rijen op de
go-live-rehearsal (bevinding 25-09-2026). Deze migratie draait de uitgebreide
eindschoonmaak nogmaals (idempotent); de velden van de handmatige
x_handling-modellen blijven staan tot die modellen handmatig worden verwijderd
(deploy-checklist stap 9).
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Voer de eindschoonmaak inclusief wees-veldrijen nogmaals uit."""
    from odoo.addons.d1_product_partner_data import hooks

    env = api.Environment(cr, SUPERUSER_ID, {})
    hooks._remove_replaced_fields(env)
    hooks._remove_stale_studio_field_rows(env)
    hooks._deactivate_remaining_studio_views(env)
    _logger.info("d1_product_partner_data: stale field row cleanup finished")
