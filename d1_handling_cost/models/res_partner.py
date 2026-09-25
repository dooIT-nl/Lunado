from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    d1_handling_id = fields.Many2one(
        comodel_name="d1.handling",
        string="Handling",
    )
