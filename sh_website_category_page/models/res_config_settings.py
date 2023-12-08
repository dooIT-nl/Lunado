# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields, models


class Website(models.Model):
    _inherit = 'website'

    category_style = fields.Selection([('style1', 'Style 1'),
                                       ('style2', 'Style 2'),
                                       ('style3', 'Style 3'),
                                       ('style4', 'Style 4'),
                                       ('style5', 'Style 5'),
                                       ('style6', 'Style 6'),
                                       ('style7', 'Style 7')], )
    category_header_style = fields.Selection([('style1', 'Style 1'),
                                              ('style2', 'Style 2'),
                                              ('style3', 'Style 3'),
                                              ('style4', 'Style 4'),
                                              ('style5', 'Style 5'),
                                              ('style6', 'Style 6')], )
    sub_category_style = fields.Selection([('style1', 'Style 1'),
                                           ('style2', 'Style 2'),
                                           ('style3', 'Style 3'),
                                           ('style4', 'Style 4'),
                                           ('style5', 'Style 5'),
                                           ('style6', 'Style 6'),
                                           ('style7', 'Style 7')],
                                          string="Subcategory Style")
    sh_website_categ_page_is_end_product = fields.Boolean(
        string="Show product in end category")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    category_style = fields.Selection(related="website_id.category_style",
                                      readonly=False)
    category_header_style = fields.Selection(
        related="website_id.category_header_style", readonly=False)
    sub_category_style = fields.Selection(
        related="website_id.sub_category_style",
        string="Subcategory Style",
        readonly=False)
    sh_website_categ_page_is_end_product = fields.Boolean(
        related="website_id.sh_website_categ_page_is_end_product",
        string="Show product in end category",
        readonly=False)
