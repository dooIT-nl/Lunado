import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # d1_use_qty en d1_use_length zijn gedefinieerd in d1_shipping_cost
    # (afhankelijkheid); deze module voegt alleen de controles toe.
    d1_saw_capacity = fields.Integer(
        string="Saw Capacity per Operation",
        help="Number of pieces sawn per operation. Required (> 0) for "
        "products with the Manufacture route.",
    )
    d1_saw_time = fields.Integer(
        string="Saw Time per Operation",
        help="Saw time per operation in seconds. Required (> 0) for "
        "products with the Manufacture route.",
    )
    d1_sawn_product_id = fields.Many2one(
        comodel_name="product.template",
        string="Sawn Product Code",
        help="Product code of the sawn variant of this product.",
    )
    d1_framecalculator = fields.Boolean(
        string="Frame Calculator",
    )

    @api.constrains("d1_use_length", "d1_use_qty")
    def _check_d1_use_length_requires_qty(self):
        """'Gebruik Lengte' vereist 'Gebruik Hoeveelheid' (pariteit met de
        Studio-automation 'Controle Product - Lengte')."""
        for template in self:
            if template.d1_use_length and not template.d1_use_qty:
                raise ValidationError(
                    _(
                        "When 'Use Length' is checked, 'Use Quantity' must "
                        "be checked as well."
                    )
                )

    @api.constrains("route_ids", "d1_saw_capacity", "d1_saw_time")
    def _check_d1_saw_values_for_manufacture(self):
        """Zaagcapaciteit en zaagtijd moeten > 0 zijn voor producten met de
        productie-route (pariteit met de Studio-automations 'Zaagcap bew >0'
        en 'Zaagtijd per bew>0'; gekoppeld aan de standaard productie-route
        i.p.v. de routenaam, besluit 17-09-2026)."""
        manufacture_route = self.env.ref(
            "mrp.route_warehouse0_manufacture", raise_if_not_found=False
        )
        if not manufacture_route:
            return
        for template in self:
            if manufacture_route not in template.route_ids:
                continue
            if template.d1_saw_capacity <= 0:
                raise ValidationError(
                    _("Saw Capacity per Operation must be greater than 0 "
                      "for products with the Manufacture route.")
                )
            if template.d1_saw_time <= 0:
                raise ValidationError(
                    _("Saw Time per Operation must be greater than 0 for "
                      "products with the Manufacture route.")
                )
