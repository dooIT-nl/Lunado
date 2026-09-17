{
    "name": "Sale Dropshipment Flag",
    "summary": "Copy the partner's dropshipment flag to sale orders (replaces Studio automations)",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "author": "dooIT B.V.",
    "website": "https://dooit.nl",
    "license": "LGPL-3",
    "depends": ["sale_management"],
    "data": [
        "views/res_partner_views.xml",
        "views/sale_order_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "description": """
        Sale Dropshipment Flag 19.0.1.0.0
        =================================
        Cluster C2 van de Studio-conversie (zie docs/studio_conversie_plan.md).

        * v1.0: initiele versie — vervangt de 2 Studio-automations
          'Verkooporder: Dropshipment overnemen van klantgegevens'
          (on_change + on_create_or_write voor API-users) door een stored
          compute die voor alle gebruikers en alle kanalen (UI en API) werkt.
          Velden hernoemd: x_studio_dropshipment -> d1_dropshipment (partner
          en order). Datamigratie en Studio-opschoning via post_init_hook.
    """,
}
