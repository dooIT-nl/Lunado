{
    "name": "Transportkosten",
    "summary": "Calculate transport costs for quotations and sales orders based on three transport classes (TK1/TK2/TK3)",
    "version": "1.2",
    "category": "Sales",
    "author": "dooIT B.V.",
    "website": "https://dooit.nl",
    "license": "LGPL-3",
    "depends": ["sale_management", "product"],
    "data": [
        "security/ir.model.access.csv",
        "data/shipping_class_data.xml",
        "data/length_bracket_data.xml",
        "data/product_data.xml",
        "data/transport_rate_data.xml",
        "wizard/res_config_settings_views.xml",
        "views/product_template_views.xml",
        "views/shipping_class_views.xml",
        "views/length_bracket_views.xml",
        "views/transport_rate_views.xml",
        "views/sale_order_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": False,
    "description": """
        Transportkosten 1.1
        ====================
        * v1.2: Qty/Length fields on order lines + native calculation (replaces Studio automations)
        * v1.1: Weight banding per piece for TK1/TK2 (heavy/mid/light pools)
        * v1.0: Initial release — transport cost calculation for TK1/TK2/TK3
    """,
}
