{
    "name": "Sale Combi Orders",
    "summary": "Combi orders across warehouses: route order lines via the configurable combi route of the order warehouse (replaces Studio automations)",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "author": "dooIT B.V.",
    "website": "https://dooit.nl",
    "license": "LGPL-3",
    "depends": ["sale_stock"],
    "data": [
        "views/product_template_views.xml",
        "views/sale_order_views.xml",
        "views/stock_warehouse_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "description": """
        Sale Combi Orders 19.0.1.0.0
        ============================
        Cluster C5 van de Studio-conversie (zie docs/studio_conversie_plan.md).

        * v1.0: initiele versie — vervangt de Studio-automations
          'Verkooporder: Combi order' en 'Verkooporderregel: Combi order'.
          Velden hernoemd: x_studio_combi -> d1_combi (order),
          x_studio_default_warehouse_id -> d1_default_warehouse_id (product).
          De hardcoded mapping magazijn 1/2 -> route 21/22 is vervangen door
          het instelbare veld 'Combi Route' op het magazijn; de migratie vult
          deze mapping (Rotterdam -> Combi RTM, Wesseling -> Combi WLS).
          Datamigratie en Studio-opschoning via post_init_hook.
    """,
}
