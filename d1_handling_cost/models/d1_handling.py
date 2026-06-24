from odoo import fields, models


class D1Handling(models.Model):
    """Handling configuration with cost brackets (lines)."""

    _name = "d1.handling"
    _description = "Handling"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, id"

    # ------------------------------------------------------------------
    # Fields
    # ------------------------------------------------------------------
    name = fields.Char(
        string="Description",
        required=True,
        tracking=True,
    )
    active = fields.Boolean(
        string="Active",
        default=True,
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )
    product_id = fields.Many2one(
        comodel_name="product.template",
        string="Product",
    )
    line_ids = fields.One2many(
        comodel_name="d1.handling.line",
        inverse_name="handling_id",
        string="Lines",
        copy=True,
    )
    d1_lunado = fields.Char(
        string="Lunado Description",
        required=False,
        tracking=False,
    )
