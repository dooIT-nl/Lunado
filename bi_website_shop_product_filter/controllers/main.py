# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import http, fields, tools, SUPERUSER_ID, _
from odoo.http import request
from odoo.tools import groupby as groupbyelem
from odoo.addons.website.controllers.main import QueryURL
from odoo.osv import expression
from operator import itemgetter
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.website_sale.controllers.main import TableCompute
from odoo.tools import lazy
from datetime import datetime, timedelta, date

_logger = logging.getLogger(__name__)


class WebsiteSaleInherit(WebsiteSale):

    def _get_compute_currency(self, pricelist, product=None):
        company = product and product._get_current_company(pricelist=pricelist,
                                                           website=request.website) or pricelist.company_id or request.website.company_id
        from_currency = (product or request.env['res.company']._get_main_company()).currency_id
        to_currency = pricelist.currency_id
        return lambda price: from_currency._convert(price, to_currency, company, fields.Date.today())

    def _get_search_domain(self, search, category, attrib_values, filter_values=False, search_in_description=True, ):
        domains = [request.website.sale_product_domain()]
        if search:
            for srch in search.split(" "):
                subdomains = [
                    [('name', 'ilike', srch)],
                    [('product_variant_ids.default_code', 'ilike', srch)]
                ]
                if search_in_description:
                    subdomains.append([('website_description', 'ilike', srch)])
                    subdomains.append([('description_sale', 'ilike', srch)])
                domains.append(expression.OR(subdomains))

        if category:
            domains.append([('public_categ_ids', 'child_of', int(category))])

        if attrib_values:
            attrib = None
            ids = []
            for value in attrib_values:
                if not attrib:
                    attrib = value[0]
                    ids.append(value[1])
                elif value[0] == attrib:
                    ids.append(value[1])
                else:
                    domains.append([('attribute_line_ids.value_ids', 'in', ids)])
                    attrib = value[0]
                    ids = [value[1]]
            if attrib:
                domains.append([('attribute_line_ids.value_ids', 'in', ids)])

        if filter_values:
            filter = None
            ids = []
            for value in filter_values:
                if not filter:
                    filter = value[0]
                    ids.append(value[1])
                elif value[0] == filter:
                    ids.append(value[1])
                else:
                    domains.append([('filter_ids.filter_value_ids', 'in', ids)])
                    filter = value[0]
                    ids = [value[1]]
            if filter:
                domains.append([('filter_ids.filter_value_ids', 'in', ids)])

        return expression.AND(domains)

    def sitemap_shop(env, rule, qs):
        if not qs or qs.lower() in '/shop':
            yield {'loc': '/shop'}

        Category = env['product.public.category']
        dom = sitemap_qs2dom(qs, '/shop/category', Category._rec_name)
        dom += env['website'].get_current_website().website_domain()
        for cat in Category.search(dom):
            loc = '/shop/category/%s' % slug(cat)
            if not qs or qs.lower() in loc:
                yield {'loc': loc}

    @http.route([
        '/shop',
        '/shop/page/<int:page>',
        '''/shop/category/<model("product.public.category", "[('website_id', 'in', (False, current_website_id))]"):category>''',
        '''/shop/category/<model("product.public.category", "[('website_id', 'in', (False, current_website_id))]"):category>/page/<int:page>''',
        '/shop/category/<abc>',
        '/shop/category/page/<int:page>/<abc>',
    ], type='http', auth="public", website=True, sitemap=sitemap_shop)
    def shop(self, page=0, category=None, search='', abc=None, min_price=0.0, max_price=0.0, ppg=False, **post):
        add_qty = int(post.get('add_qty', 1))
        try:
            min_price = float(min_price)
        except ValueError:
            min_price = 0
        try:
            max_price = float(max_price)
        except ValueError:
            max_price = 0

        Category = request.env['product.public.category']
        if category:
            category = Category.search([('id', '=', int(category))], limit=1)
            if not category or not category.can_access_from_current_website():
                raise NotFound()
        else:
            category = Category

        website = request.env['website'].get_current_website()
        if ppg:
            try:
                ppg = int(ppg)
                post['ppg'] = ppg
            except ValueError:
                ppg = False
        if not ppg:
            ppg = website.shop_ppg or 20

        ppr = website.shop_ppr or 4

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [[int(x) for x in v.split("-")] for v in attrib_list if v]
        attributes_ids = {v[0] for v in attrib_values}
        attrib_set = {v[1] for v in attrib_values}
        filter_list = request.httprequest.args.getlist('filter')
        
        filter_values = [[int(x) for x in v.split("-")] for v in filter_list if v]
        filter_ids = {v[0] for v in filter_values}
        filter_set = {v[1] for v in filter_values}

        domain = self._get_search_domain(search, category, attrib_values, filter_values)

        keep = QueryURL('/shop', category=category and int(category), search=search, attrib=attrib_list, min_price=min_price, max_price=max_price, order=post.get('order'))
        now = datetime.timestamp(datetime.now())
        pricelist = request.env['product.pricelist'].browse(request.session.get('website_sale_current_pl'))
        if not pricelist or request.session.get('website_sale_pricelist_time', 0) < now - 60*60: # test: 1 hour in session
            pricelist = website.get_current_pricelist()
            request.session['website_sale_pricelist_time'] = now
            request.session['website_sale_current_pl'] = pricelist.id

        request.update_context(pricelist=pricelist.id, partner=request.env.user.partner_id)

        filter_by_price_enabled = website.is_view_active('website_sale.filter_products_price')
        if filter_by_price_enabled:
            company_currency = website.company_id.currency_id
            conversion_rate = request.env['res.currency']._get_conversion_rate(
                company_currency, pricelist.currency_id, request.website.company_id, fields.Date.today())
        else:
            conversion_rate = 1

        url = "/shop"
        if search:
            post["search"] = search
            # AllBrands = request.env['product.brand'].search([('name','ilike',search)])
            # ids = []
            # for i in AllBrands:
            #     ids.append(i.id)
            # domain_new = [('brand_id', 'in', ids)]
        if attrib_list:
            post['attrib'] = attrib_list

        if filter_list:
            post['filter'] = filter_list

        options = self._get_search_options(
            category=category,
            attrib_values=attrib_values,
            pricelist=pricelist,
            min_price=min_price,
            max_price=max_price,
            conversion_rate=conversion_rate,
            **post
        )
        fuzzy_search_term, product_count, search_product = self._shop_lookup_products(attrib_set, options, post, search, website)

        filter_by_price_enabled = website.is_view_active('website_sale.filter_products_price')
        if filter_by_price_enabled:
            # TODO Find an alternative way to obtain the domain through the search metadata.
            Product = request.env['product.template'].with_context(bin_size=True)
            domain = self._get_search_domain(search, category, attrib_values, filter_values)

            # This is ~4 times more efficient than a search for the cheapest and most expensive products
            from_clause, where_clause, where_params = Product._where_calc(domain).get_sql()
            query = f"""
                SELECT COALESCE(MIN(list_price), 0) * {conversion_rate}, COALESCE(MAX(list_price), 0) * {conversion_rate}
                  FROM {from_clause}
                 WHERE {where_clause}
            """
            request.env.cr.execute(query, where_params)
            available_min_price, available_max_price = request.env.cr.fetchone()

            if min_price or max_price:
                # The if/else condition in the min_price / max_price value assignment
                # tackles the case where we switch to a list of products with different
                # available min / max prices than the ones set in the previous page.
                # In order to have logical results and not yield empty product lists, the
                # price filter is set to their respective available prices when the specified
                # min exceeds the max, and / or the specified max is lower than the available min.
                if min_price:
                    min_price = min_price if min_price <= available_max_price else available_min_price
                    post['min_price'] = min_price
                if max_price:
                    max_price = max_price if max_price >= available_min_price else available_max_price
                    post['max_price'] = max_price
        
        Product = request.env['product.template'].with_context(bin_size=True)
        setting = request.env['res.config.settings'].sudo().search([], order=' id desc', limit=1)
        list_of_product = []
        if category:    
            parent_category_ids = [category.id]
            current_category = category
            while current_category.parent_id:
                parent_category_ids.append(current_category.parent_id.id)
                current_category = current_category.parent_id

        # if request.env.user.partner_id.product_ids:
        #     for p_id in request.env.user.partner_id.product_ids:
        #         list_of_product.append(p_id.id)
        # if request.env.user.partner_id.product_categ_ids:
        #     for c_id in request.env.user.partner_id.product_categ_ids:
        #         product_categ_ids = request.env['product.template'].sudo().search([('categ_id','=',c_id.id)])
        #         for category_ids in product_categ_ids:
        #             list_of_product.append(category_ids.id)
        # if request.env.user.partner_id:
        #     domain+= [('id','in',list_of_product)] 

        # if setting.visitor_product_ids:
        #     for p_id in setting.visitor_product_ids:
        #         list_of_product.append(p_id.id)
        # if setting.visitor_product_categ_ids:
        #     for c_id in setting.visitor_product_categ_ids:
        #         product_categ_ids = request.env['product.template'].sudo().search([('categ_id','=',c_id.id)])
        #         for category_ids in product_categ_ids:
        #             list_of_product.append(category_ids.id)
        # if setting:
        #     domain+= [('id','in',list_of_product)] 
        search_product = Product.search(domain)
        search_categories = False
        if search:
            categories = search_product.mapped('public_categ_ids')
            search_categories = Category.search([('id', 'parent_of', categories.ids)] + request.website.website_domain())
            categs = search_categories.filtered(lambda c: not c.parent_id)
        else:
            categs = Category.search([('parent_id', '=', False)] + request.website.website_domain())

        website_domain = website.website_domain()
        categs_domain = [('parent_id', '=', False)] + website_domain
        if search:
            search_categories = Category.search(
                [('product_tmpl_ids', 'in', search_product.ids)] + website_domain
            ).parents_and_self
            categs_domain.append(('id', 'in', search_categories.ids))
        else:
            search_categories = Category
        categs = lazy(lambda: Category.search(categs_domain))

        if category:
            url = "/shop/category/%s" % slug(category)



        product_count = len(search_product)
        pager = website.pager(url=url, total=product_count, page=page, step=ppg, scope=7, url_args=post)
        products = Product.search(domain, limit=ppg, offset=pager['offset'], order=self._get_search_order(post))
        ProductAttribute = request.env['product.attribute']
        ProductFilter = request.env['product.filter']
        
        if products:
            # get all products without limit
            attributes = lazy(lambda: ProductAttribute.search([
                ('product_tmpl_ids', 'in', search_product.ids)
            ]))
        else:
            attributes = lazy(lambda: ProductAttribute.browse(attributes_ids))
        filters = grouped_tasks = None

        if products:
            # get all products without limit
            selected_products = Product.search(domain, limit=False)
            
            filters = ProductFilter.search([('filter_value_ids', '!=', False), ('filter_ids.product_tmpl_id', 'in', selected_products.ids)])
            
        else:
            filters = ProductFilter.browse(filter_ids)

        filter_group = request.env['group.filter'].search([])

        applied_filter = False
        if filter_values:
            applied_filter = True

        if filter_group:
            grouped_tasks = [request.env['product.filter'].concat(*g) for k, g in groupbyelem(filters, itemgetter('group_id'))]
        else:
            grouped_tasks = [filters]
        
        prods  = Product.sudo().search(domain)
        request.website.sudo().get_dynamic_count(prods)

        layout_mode = request.session.get('website_sale_shop_layout_mode')
        if not layout_mode:
            if website.viewref('website_sale.products_list_view').active:
                layout_mode = 'list'
            else:
                layout_mode = 'grid'
            request.session['website_sale_shop_layout_mode'] = layout_mode

        products_prices = lazy(lambda: products._get_sales_prices(pricelist))

        values = {
            'search': fuzzy_search_term or search,
            'original_search': fuzzy_search_term and search,
            'order': post.get('order', ''),
            'category': category,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'filter_set': filter_set,
            'filter_values': filter_values,
            'pager': pager,
            'pricelist': pricelist,
            'add_qty': add_qty,
            'grouped_tasks':grouped_tasks,
            'products': products,
            'search_product': search_product,
            'search_count': product_count,  # common for all searchbox
            'bins': lazy(lambda: TableCompute().process(products, ppg, ppr)),
            'ppg': ppg,
            'ppr': ppr,
            'categories': categs,
            'attributes': attributes,
            'filters': filters,
            'keep': keep,
            'search_categories_ids': search_categories.ids,
            'layout_mode': layout_mode,
            'products_prices': products_prices,
            'get_product_prices': lambda product: lazy(lambda: products_prices[product.id]),
            'float_round': tools.float_round,
        }
        if filter_by_price_enabled:
            values['min_price'] = min_price or available_min_price
            values['max_price'] = max_price or available_max_price
            values['available_min_price'] = tools.float_round(available_min_price, 2)
            values['available_max_price'] = tools.float_round(available_max_price, 2)
        if 'seo_url' in values:
            for j,k in values['seo_url'].items():
                if k == False or k == '':
                    pro = Product.sudo().search([('id','=',int(j))],limit=1)
                    values['seo_url'].update({j : slug(pro)})
        if category:
            values['main_object'] = category
        values.update(self._get_additional_shop_values(values))
        return request.render("website_sale.products", values)
    

    