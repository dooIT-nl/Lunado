# -*- coding: utf-8 -*-
{
    'name': 'DeliveryMatch',
    'version': '1.0',
    'license': 'LGPL-3',
    'author': 'Deliverymatch Development Team',
    'summary': 'Deliverymatch',
    'description': 'description...',
    'category': 'services',
    'website': 'https://www.deliverymatch.eu/over-ons',
    'depends': ['sale', 'product', 'stock', 'base'],
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
        "views/customer_partners.xml"
    ],
    'application': True,
    'installable': True
}
