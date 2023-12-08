# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo.http import request
from odoo import http
from odoo.addons.http_routing.models.ir_http import slug

class Main(http.Controller):

    @http.route('/sh_category_snippet/get_categories', type='json', auth="none", methods=['post'], website=True)
    def get_categories(self, item_template=False, categs_ids=False, order_by=False, is_show_categ_image=False, is_show_categ_desc=False, is_show_categ_prod_count=False):

        data = ''
        order = "sequence asc"
        if order_by:
            order = order_by

        categs_domain = request.website.website_domain()
        list_categ_ids = []
        domain = []
        if categs_ids:
            for categ_id in categs_ids:
                if type(categ_id) != int:
                    categ_id = int(categ_id)
                list_categ_ids.append(categ_id)

        if list_categ_ids:
            categs_domain.append(('id', 'in', list_categ_ids))

        categories = request.env['product.public.category'].sudo().search(
            categs_domain,
            order=order,
        )

        if categories and item_template:
            list_categs = []
            multiwebsite_domain = request.website.website_domain()
            for category in categories:

                domain = [
                    ('public_categ_ids', 'child_of', category.id),
                    ("sale_ok", "=", True),
                    ('website_published', '=', True)
                ]

                domain = domain + multiwebsite_domain

                products = request.env['product.template'].search(domain)
                product_count = 'No'
                if products:
                    product_count = len(products.ids)
                url = "/shop/category/%s" % slug(category)
                dic = {
                    'categ_name': category.name,
                    'product_count':  product_count,
                    'categ_url': url,
                    'categ_img_url': '/web/image/product.public.category/%s/image_1920' % str(category.id),
                    'categ_desc': category.sh_category_snippet_desc,
                }
                list_categs.append(dic)

            data = request.env["ir.ui.view"].sudo()._render_template(item_template, values={
                'list_categs': list_categs,
                'is_show_categ_image': is_show_categ_image,
                'is_show_categ_desc': is_show_categ_desc,
                'is_show_categ_prod_count': is_show_categ_prod_count,
            })
            # data = data.decode("utf-8")

        values = {
            'data': data,
        }

        return values
