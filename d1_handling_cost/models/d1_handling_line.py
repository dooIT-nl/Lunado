from odoo import fields, models


class D1HandlingLine(models.Model):
    """Single cost bracket within a handling configuration."""

    _name = "d1.handling.line"
    _description = "Handling Line"
    _order = "sequence, id"

    # ------------------------------------------------------------------
    # Fields
    # ------------------------------------------------------------------
    name = fields.Char(
        string="Description",
    )
    handling_id = fields.Many2one(
        comodel_name="d1.handling",
        string="Handling",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(
        string="Sequence",
    )
    currency_id = fields.Many2one(
        related="handling_id.currency_id",
        string="Currency",
    )
    amount = fields.Monetary(
        string="Amount",
        currency_field="currency_id",
    )
    value_from = fields.Monetary(
        string="From",
        currency_field="currency_id",
    )
    total = fields.Monetary(
        string="To",
        currency_field="currency_id",
    )
