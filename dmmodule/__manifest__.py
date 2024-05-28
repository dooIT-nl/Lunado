# -*- coding: utf-8 -*-
{
    'name': 'DeliveryMatch shipping integration',
    'version': '1.0',
    'license': 'LGPL-3',
    'author': 'Deliverymatch Development Team',
    'summary': 'Deliverymatch',
    'description': 'DeliveryMatch shipping integration',
    'category': 'services',
    'website': 'https://deliverymatch.eu/en',
    'depends': ['sale', 'product', 'stock', 'base'],
    'images': ['static/description/banner.jpg', 'static/description/services.jpg'],
    'data': [
        "security/ir.model.access.csv",
        "views/deliverymatch_index_view.xml",
        "views/deliver_options_view.xml",
        "views/sale_order.xml",
        "views/product.xml",
        "views/stock_picking.xml",
        "views/deliverymatch_config.xml",
        "views/stock_warehouse.xml",
        "views/warehouses_popup_view.xml",
        "views/popup_wizard_views.xml",
        "views/operation_type.xml",
        "views/customer_partners.xml",
        "views/product_packaging.xml",
        "views/package_table.xml",
        "views/label_table.xml",
        "views/stock_move_line.xml",
        "views/stock_package_type.xml",
    ],
    'application': True,
    'installable': True
}
