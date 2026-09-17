import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    d1_delivery_picking_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Delivery Operation Type",
        help="Default operation type (Deliver To) for purchase orders of "
        "this vendor. Applied together with the incoterm below, unless the "
        "order's operation type is excluded (e.g. Dropship).",
    )
    d1_incoterm_id = fields.Many2one(
        comodel_name="account.incoterms",
        string="Delivery Incoterm",
        help="Default incoterm for purchase orders of this vendor; applied "
        "together with the delivery operation type.",
    )
