{
    "name": "Sale Extra Service per Product Category",
    "summary": "Automatically add and sum an extra service line on sale orders based on the product category (replaces Studio automation)",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "author": "dooIT B.V.",
    "website": "https://dooit.nl",
    "license": "LGPL-3",
    "depends": ["d1_shipping_cost"],
    "data": [
        "views/product_category_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "description": """
        Sale Extra Service per Product Category 19.0.1.0.0
        ==================================================
        Cluster C4 van de Studio-conversie (zie docs/studio_conversie_plan.md).

        * v1.0: initiele versie — vervangt de Studio-automation
          'Verkooporderregel: Voeg dienst toe'. Veld hernoemd:
          product.category x_studio_extra_dienst ->
          d1_extra_service_product_id. De dienstregel wordt per
          dienst-artikel gesommeerd (verbetering: de Studio-versie telde
          regels van verschillende diensten bij elkaar op).
          Datamigratie en Studio-opschoning via post_init_hook.
    """,
}
