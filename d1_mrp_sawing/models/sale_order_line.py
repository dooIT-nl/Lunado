import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # d1_qty, d1_length, d1_use_qty en d1_use_length zijn gedefinieerd in
    # d1_shipping_cost (afhankelijkheid), inclusief de qty x lengte-logica
    # voor product_uom_qty. Deze module voegt gewicht en frames toe.
    d1_weight = fields.Float(
        string="Weight",
        compute="_compute_d1_weight",
        store=True,
    )
    d1_frame_id = fields.Char(
        string="Frame ID",
        help="Frame identification, filled by the frame calculator.",
    )
    d1_frame_nr = fields.Char(
        string="Frame Number",
        compute="_compute_d1_frame_nr",
        store=True,
        help="Order number (without the leading 'S') combined with the last "
        "3 characters of the Frame ID.",
    )
    d1_qty_var_name = fields.Char(
        string="Qty Var Name",
    )

    @api.depends("product_uom_qty", "product_uom_id", "product_id.weight")
    def _compute_d1_weight(self):
        """Gewicht van de regel = besteld aantal (in producteenheid) x
        productgewicht. Gebaseerd op het opgeslagen variantgewicht
        (product_id.weight); de template- en delivery-varianten van dit veld
        zijn niet-opgeslagen computes en tijdens create onbetrouwbaar."""
        for line in self:
            if not line.product_id:
                line.d1_weight = 0.0
                continue
            qty = line.product_uom_id._compute_quantity(
                line.product_uom_qty, line.product_id.uom_id
            )
            line.d1_weight = qty * line.product_id.weight

    @api.depends("d1_frame_id", "order_id.name")
    def _compute_d1_frame_nr(self):
        """Framenummer = ordernummer (zonder voorloop-'S') + '-' + laatste 3
        tekens van het Frame ID (pariteit met het Studio-computeveld)."""
        for line in self:
            frame_id = line.d1_frame_id or ""
            if not frame_id:
                line.d1_frame_nr = False
                continue
            order_name = line.order_id.name or ""
            order_part = (
                order_name[1:] if order_name.startswith("S") else order_name
            )
            frame_suffix = frame_id[-3:] if len(frame_id) >= 3 else frame_id
            if order_part and frame_suffix:
                line.d1_frame_nr = "%s-%s" % (order_part, frame_suffix)
            elif order_part:
                line.d1_frame_nr = order_part
            else:
                line.d1_frame_nr = False
