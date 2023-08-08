# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
from odoo import models, api, fields, _
from odoo.tools import format_datetime, formatLang

class InheritProductPricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    def _is_applicable_for(self, product, qty_in_product_uom):
        self.ensure_one()
        product.ensure_one()
        res = True

        is_product_template = product._name == 'product.template'
        if self.min_quantity and qty_in_product_uom < self.min_quantity:
            res = False

        elif self.categ_id:
            # Applied on a specific category
            cat = product.categ_id
            while cat:
                if cat.id == self.categ_id.id:
                    break
                cat = cat.parent_id
            if not cat:
                res = False
        else:
            if is_product_template:
                if self.product_tmpl_id and product.id != self.product_tmpl_id.id:
                    res = False
                elif self.product_package_id and product.id != self.product_package_id.id:
                    res = False
                elif self.product_id and not (
                    product.product_variant_count == 1
                    and product.product_variant_id.id == self.product_id.id
                ):
                    # product self acceptable on template if has only one variant
                    res = False
            else:
                if self.product_tmpl_id and product.product_tmpl_id.id != self.product_tmpl_id.id:
                    res = False
                elif self.product_id and product.id != self.product_id.id:
                    res = False
        return res
    
    @api.depends('applied_on', 'categ_id', 'product_tmpl_id', 'product_id', 'compute_price', 'fixed_price',
                 'pricelist_id', 'percent_price', 'price_discount', 'price_surcharge', 'package_id')
    def _compute_name_and_price(self):
        for item in self:
            if item.categ_id and item.applied_on == '2_product_category':
                item.name = _("Category: %s") % (item.categ_id.display_name)
            elif item.product_tmpl_id and item.applied_on == '1_product':
                item.name = _("Product: %s") % (
                    item.product_tmpl_id.display_name)
            elif item.product_id and item.applied_on == '0_product_variant':
                item.name = _("Variant: %s") % (item.product_id.with_context(
                    display_default_code=False).display_name)
            elif item.applied_on == '4_package' and not item.product_id and item.product_package_id and item.package_id:
                item.name = (item.product_package_id.name + "[" + item.package_id.display_name + "]")
            else:
                item.name = _("All Products")

            if item.compute_price == 'fixed':
                item.price = formatLang(
                    item.env, item.fixed_price, monetary=True, dp="Product Price", currency_obj=item.currency_id)
            elif item.compute_price == 'percentage':
                item.price = _("%s %% discount", item.percent_price)
            else:
                item.price = _("%(percentage)s %% discount and %(price)s surcharge",
                               percentage=item.price_discount, price=item.price_surcharge)

    package_id = fields.Many2one(
        'product.packaging',
        string='Select Product Pack'
    )

    applied_on = fields.Selection(
        selection_add=[('4_package', 'Product Pack')],
        string="Apply On",
        default='3_global',
        required=True,
                ondelete={'4_package': lambda recs: recs.write(
                    {'applied_on': 'odoo'})},
        help="Pricelist Item applicable on selected option")

    product_package_id = fields.Many2one('product.product', string='Product')
