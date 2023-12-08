# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
{
    "name": "Website Category Page",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "version": "16.0.1",
    "category": "Website",
    "summary": "Shop Category page, Category page, E-commerce Category page, Odoo Category Page, Website Category page,ecommerce Category page, website categories, category page on shop Odoo",
    "description": """This module useful to show category page for shop.Are you running the store with a large catalog of products? Wanna bring store usability to new high level? Than This module useful to show category page for shop. It's provide easy catalog images to make the display of categories list more presentable.Grab users attention on your store page, providing them with the immediate loadable categories listing. The default odoo category bar in shop doesn't provide a user-friendly way to browse catalogs. Our extension allows you to use better navigation displaying all categories list on the category page.""",
    "depends": ['website_sale'],
    "data": [
        'views/res_config_settings_views.xml',
        'views/product_public_category_views.xml',
        'views/website_sale_templates.xml',
        'views/shop_by_category_templates.xml',
        'data/website_menus_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'sh_website_category_page/static/src/scss/sh_website_category_page.scss',
            'sh_website_category_page/static/src/css/sh_website_category.css',
        ],
    },
    "images": [
        'static/description/background.png',
    ],
    "license": "OPL-1",
    "auto_install": False,
    "application": True,
    "installable": True,
    "price": 25,
    "currency": "EUR",
}
