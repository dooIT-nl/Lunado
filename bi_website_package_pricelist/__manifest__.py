# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

{
    "name": "Product Packaging in Sales/eCommerce",
    "version": "16.0.0.6",
    "category": "Website",
    "depends": ['sale_management', 'website_sale', 'stock'],
    "author": "BrowseInfo",
    "license": "OPL-1",
    "summary": '',
    "description": """ """,
    "website": "https://www.browseinfo.in",
    "price": "",
    "currency": "",
    "data": [
            "security/ir.model.access.csv",
            'report/report_template.xml',
            "wizard/product_package_wizard_view.xml",
            'views/account_move_views.xml',
            "views/web_pricelist_view.xml",
            "views/sale_order_view.xml",
            "views/templates.xml",
        ],
    'assets': {
        'web.assets_frontend': [
             'bi_website_package_pricelist/static/src/js/website_package_pricelist.js',
             'bi_website_package_pricelist/static/src/js/website_fontend.js',
        ]
    },
    "auto_install": False,
    "installable": True,
}
