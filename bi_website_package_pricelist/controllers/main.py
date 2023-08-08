# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
from odoo import http, fields
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.tools.json import scriptsafe as json_scriptsafe
from odoo.addons.payment import utils as payment_utils


class WebsiteSaleInherit(WebsiteSale):

    @http.route(['/shop/cart/update_json'], type='json', auth="public", methods=['POST'], website=True, csrf=False)
    def cart_update_json(
        self, product_id, line_id=None, add_qty=None, set_qty=None, display=True,
        product_custom_attribute_values=None, no_variant_attribute_values=None, product_packaging_id=None, **kw
    ):
        order = request.website.sale_get_order(force_create=True)
        if order.state != 'draft':
            request.website.sale_reset()
            if kw.get('force_create'):
                order = request.website.sale_get_order(force_create=True)
            else:
                return {}

        if product_custom_attribute_values:
            product_custom_attribute_values = json_scriptsafe.loads(product_custom_attribute_values)

        if no_variant_attribute_values:
            no_variant_attribute_values = json_scriptsafe.loads(no_variant_attribute_values)
        order_line_id = False
        product = request.env['product.product'].sudo().browse(product_id)
        if product_packaging_id != None and add_qty != None and set_qty == None:
            price = request.env['product.package.wizard'].sudo().add_product_package(int(product_packaging_id))
            order_line_id = request.env['sale.order.line'].sudo().search([("order_id", '=', order.id), ("product_id", '=', product_id), ("product_packaging_id", '=', int(product_packaging_id))])
            if not order_line_id:
                order_line_id = request.env['sale.order.line'].sudo().create({'order_id': order.id, 'product_id': product_id, "name": product.display_name, 'product_uom_qty': 0, 'product_packaging_id': product_packaging_id, 'price_unit': price})
            values = order._cart_update(
                product_id=product_id,
                line_id=order_line_id.id if order_line_id else None,
                add_qty=add_qty,
                set_qty=set_qty,
                product_custom_attribute_values=product_custom_attribute_values,
                no_variant_attribute_values=no_variant_attribute_values,
                **kw
            )
        else:
            if line_id == None:           
                order_line_id = request.env['sale.order.line'].sudo().search([("order_id", '=', order.id), ("product_id", '=', product_id), ("product_packaging_id", '=', False)])
            else:
                order_line_id = request.env['sale.order.line'].sudo().browse(line_id)
            if set_qty == None and add_qty != None and not order_line_id:
                price = order.pricelist_id._get_product_price(product, add_qty)
                order_line_id = request.env['sale.order.line'].sudo().create({'order_id': order.id, 'product_id': product_id, "name": product.display_name, 'product_uom_qty': 0, 'price_unit': price})
            values = order._cart_update(
                product_id=product_id,
                line_id=order_line_id.id if order_line_id else line_id,
                add_qty=add_qty,
                set_qty=set_qty,
                product_custom_attribute_values=product_custom_attribute_values,
                no_variant_attribute_values=no_variant_attribute_values,
                **kw
            )
        if not order_line_id and product_packaging_id != None and values.get('line_id') and add_qty != None and set_qty == None:
            order_line_id = request.env['sale.order.line'].sudo().browse(values.get('line_id')).exists()
            if order_line_id:
                if price:
                    order_line_id.write({'product_packaging_id': product_packaging_id, 'price_unit': price})
                else:
                    order_line_id.write({'product_packaging_id': product_packaging_id})
        request.session['website_sale_cart_quantity'] = order.cart_quantity

        if not order.cart_quantity:
            request.website.sale_reset()
            return values

        values['cart_quantity'] = order.cart_quantity
        values['minor_amount'] = payment_utils.to_minor_currency_units(
            order.amount_total, order.currency_id
        ),
        values['amount'] = order.amount_total

        if not display:
            return values

        values['website_sale.cart_lines'] = request.env['ir.ui.view']._render_template(
            "website_sale.cart_lines", {
                'website_sale_order': order,
                'date': fields.Date.today(),
                'suggested_products': order._cart_accessories()
            }
        )
        values['website_sale.short_cart_summary'] = request.env['ir.ui.view']._render_template(
            "website_sale.short_cart_summary", {
                'website_sale_order': order,
            }
        )
        
        return values

    def _prepare_product_values(self, product, category, search, **kwargs):
        res = super(WebsiteSaleInherit, self)._prepare_product_values(product=product, category=category, search=search,
                                                                      **kwargs)
        packaging = request.env['product.packaging'].sudo().search([('product_id.product_tmpl_id', '=', product.id)])
        if packaging:
            res.update({'packaging': packaging})
        return res

    @http.route(['/shop/product/packaging'], type='json', auth="public", methods=['POST'], website=True)
    def product_pricelist_price(self, **post):
        price = 0.0
        if post.get('qty_val'):
            price = request.env['product.package.wizard'].add_product_package(int(post.get('qty_val')))
        return price
