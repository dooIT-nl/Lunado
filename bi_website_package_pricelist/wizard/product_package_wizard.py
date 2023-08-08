# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.http import request


class Pricelist(models.Model):
    _inherit = "product.pricelist"

    def _get_applicable_rules(self, products, date, rules=False,  **kwargs):
        res = super(Pricelist, self)._get_applicable_rules(products=products, date=date, **kwargs)
        if self._context.get('price_id'):
            res = self._context.get('price_id')
        return res


class ProductPackageWizard(models.TransientModel):
    _name = 'product.package.wizard'
    _description = 'Product Package Wizard'
    
    def _get_package_records(self):        
        lst = []
        ctx = self.env.context
        product_id = ctx.get('default_product_tmpl_id')
        if product_id is not None:
            product_packaging_ids = self.env['product.packaging'].sudo().search([('product_id.product_tmpl_id', '=', product_id)])
            for data in product_packaging_ids:
                lst.append((data.id, data.name + ', ' + 'Quantity :' + ' ' + str(data.qty)))
        return lst
    
    product_tmpl_id = fields.Many2one('product.template', string='Product')
    package_selection = fields.Selection(_get_package_records, string="Product Package")
    
    def add_product_package(self, qty_val=False):
        price = False
        res = self.env['res.config.settings'].sudo().search([], limit=1, order="id desc")
        if self:
            ctx = self.env.context
            active_id = ctx.get('active_id')
            order_line = self.env['sale.order.line'].browse(active_id)
            packaging = self.env['product.packaging'].sudo().search([('id', '=', int(self.package_selection))])
            if packaging:
                order_line.product_qty = packaging.qty * order_line.product_uom_qty
                order_line.product_packaging_id = packaging.id
            if res.product_pricelist_setting == 'advanced':
                if packaging and order_line.order_id.pricelist_id:
                    price_id = order_line.order_id.pricelist_id.item_ids.filtered(lambda l: l.product_package_id == order_line.product_id and l.applied_on == '4_package' and l.package_id.id == int(self.package_selection))
                    if price_id:
                        order_line.price_unit = order_line.order_id.pricelist_id.with_context(price_id=price_id)._get_product_price(order_line.product_id, order_line.product_uom_qty)
                        price = order_line.price_unit
                    else:
                        if packaging and packaging.product_id:
                            price = packaging.product_id.list_price
        else:
            packaging = self.env['product.packaging'].sudo().search([('id', '=', int(qty_val))])
            if self.env.user.partner_id and self.env.user.partner_id.property_product_pricelist:
                pricelist_id = self.env.user.partner_id.property_product_pricelist
                if res.product_pricelist_setting == 'advanced':
                    if packaging and pricelist_id:
                        price_id = pricelist_id.item_ids.filtered(lambda l: l.product_package_id == packaging.product_id and l.applied_on == '4_package' and l.package_id.id == packaging.id)
                        price = pricelist_id.with_context(price_id=price_id)._get_product_price(packaging.product_id, packaging.qty)
                    elif packaging and packaging.product_id:
                        price = packaging.product_id.list_price
        return price
