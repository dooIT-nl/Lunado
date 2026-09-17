import logging
import math

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    d1_qty = fields.Float(
        string="Sawing Quantity",
        compute="_compute_d1_sale_line_values",
        store=True,
        readonly=False,
        help="Sawing quantity from the linked sale order line.",
    )
    d1_length = fields.Float(
        string="Length",
        compute="_compute_d1_sale_line_values",
        store=True,
        readonly=False,
        help="Length from the linked sale order line.",
    )
    d1_frame_nr = fields.Char(
        string="Frame Number",
        compute="_compute_d1_sale_line_values",
        store=True,
        readonly=False,
        help="Frame number from the linked sale order line.",
    )
    d1_production_time = fields.Float(
        string="Production Time",
        compute="_compute_d1_production_time",
        store=True,
        help="Saw time in minutes: ceil(quantity / saw capacity) x saw time "
        "per operation / 60, rounded to whole minutes.",
    )

    @api.depends(
        "move_dest_ids.sale_line_id.d1_qty",
        "move_dest_ids.sale_line_id.d1_length",
        "move_dest_ids.sale_line_id.d1_frame_nr",
    )
    def _compute_d1_sale_line_values(self):
        """Neem hoeveelheid, lengte en framenummer over van de verkoopregel
        waarvoor deze productieorder is aangemaakt (pariteit met de
        Studio-computevelden). Handmatig aanpasbaar (readonly=False) voor
        productieorders zonder verkoopkoppeling."""
        for production in self:
            sale_line = production.move_dest_ids.sale_line_id[:1]
            if sale_line:
                production.d1_qty = sale_line.d1_qty
                production.d1_length = sale_line.d1_length
                production.d1_frame_nr = sale_line.d1_frame_nr
            else:
                production.d1_qty = production.d1_qty
                production.d1_length = production.d1_length
                production.d1_frame_nr = production.d1_frame_nr

    @api.depends(
        "d1_qty",
        "product_id.d1_saw_capacity",
        "product_id.d1_saw_time",
    )
    def _compute_d1_production_time(self):
        """Zaagformule (pariteit met het Studio-computeveld
        'Productietijd'): aantal bewerkingen = hoeveelheid / zaagcapaciteit,
        naar boven afgerond; tijd = bewerkingen x zaagtijd (sec) / 60,
        afgerond op hele minuten."""
        for production in self:
            capacity = production.product_id.d1_saw_capacity
            saw_time = production.product_id.d1_saw_time
            if capacity <= 0 or saw_time <= 0:
                production.d1_production_time = 0.0
                continue
            operations = math.ceil(production.d1_qty / capacity)
            production.d1_production_time = round(
                operations * (saw_time / 60.0)
            )
