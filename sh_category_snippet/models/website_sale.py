# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields


class ProductPublicCategory(models.Model):
    _inherit = "product.public.category"

    sh_category_snippet_desc = fields.Text(string="Description")
