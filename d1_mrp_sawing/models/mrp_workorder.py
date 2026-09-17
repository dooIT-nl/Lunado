import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    d1_qty = fields.Float(
        string="Sawing Quantity",
        related="production_id.d1_qty",
    )
    d1_length = fields.Float(
        string="Length",
        related="production_id.d1_length",
    )
    d1_production_time = fields.Float(
        string="Production Time Finished Product",
        related="production_id.d1_production_time",
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Vul de (verwachte) duur met de berekende productietijd bij het
        aanmaken van werkorders."""
        workorders = super().create(vals_list)
        workorders._d1_fill_duration()
        return workorders

    def write(self, vals):
        """Vul de (verwachte) duur opnieuw wanneer status of controles
        wijzigen (pariteit met de triggers van de Studio-automations
        'Werkorder: Duur vullen' / 'Verwachte duur vullen')."""
        res = super().write(vals)
        if not self.env.context.get("d1_skip_duration_fill") and (
            "state" in vals or "check_ids" in vals
        ):
            self._d1_fill_duration()
        return res

    def _d1_fill_duration(self):
        """Zet verwachte én werkelijke duur op de berekende productietijd van
        de productieorder (besluit 17-09-2026: huidig gedrag behouden, beide
        vullen). Werkorders zonder productietijd blijven ongemoeid."""
        for workorder in self.with_context(d1_skip_duration_fill=True):
            production_time = workorder.production_id.d1_production_time
            if not production_time:
                continue
            if workorder.duration_expected != production_time:
                workorder.duration_expected = production_time
            if workorder.duration != production_time:
                workorder.duration = production_time
