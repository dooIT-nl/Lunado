import logging

from odoo import models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _d1_sync_extra_service_lines(self):
        """Synchroniseer de dienstregels van de order.

        Pariteit met de Studio-automation 'Verkooporderregel: Voeg dienst
        toe', met een correctie: de hoeveelheid wordt per dienst-artikel
        gesommeerd (de Studio-versie telde regels van verschillende diensten
        bij elkaar op).

        Regels:
        * Alleen orders zonder bronndocument (origin) in offerte-status.
        * Per regel met een product waarvan de categorie een Extra dienst
          heeft: sommeer de zaaghoeveelheid (d1_qty) per dienst-artikel.
        * Bestaat er al een regel met het dienst-artikel, dan wordt de
          hoeveelheid bijgewerkt; anders wordt de regel toegevoegd.
        * Dienstregels worden niet verwijderd als de som 0 wordt (pariteit).
        """
        for order in self:
            if order.origin or order.state not in ("draft", "sent"):
                continue
            totals = {}
            for line in order.order_line:
                if line.display_type:
                    continue
                service = line.product_template_id.categ_id.d1_extra_service_product_id
                if not service or line.product_template_id == service:
                    continue
                totals[service] = totals.get(service, 0.0) + line.d1_qty
            for service, qty in totals.items():
                service_line = order.order_line.filtered(
                    lambda l: l.product_template_id == service
                )[:1]
                ctx_order = order.with_context(d1_skip_extra_service=True)
                if service_line:
                    if service_line.product_uom_qty != qty:
                        service_line.with_context(
                            d1_skip_extra_service=True
                        ).product_uom_qty = qty
                else:
                    ctx_order.order_line = [
                        (0, 0, {
                            "product_id": service.product_variant_id.id,
                            "product_uom_qty": qty,
                        })
                    ]
