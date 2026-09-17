{
    "name": "Purchase Partner Delivery Defaults",
    "summary": "Default operation type and incoterm from the vendor on purchase orders (replaces Studio automation)",
    "version": "19.0.1.0.0",
    "category": "Purchases",
    "author": "dooIT B.V.",
    "website": "https://dooit.nl",
    "license": "LGPL-3",
    "depends": ["purchase_stock"],
    "data": [
        "views/res_partner_views.xml",
        "views/stock_picking_type_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "description": """
        Purchase Partner Delivery Defaults 19.0.1.0.0
        =============================================
        Cluster C3 van de Studio-conversie (zie docs/studio_conversie_plan.md).

        * v1.0: initiele versie — vervangt de Studio-automation 'Vul Leveren
          aan en Leverconditie'. Velden hernoemd:
          x_studio_type_levering -> d1_delivery_picking_type_id,
          x_studio_incoterm_id -> d1_incoterm_id.
          De hardcoded uitsluiting van operatietype id 10 (Dropship) is
          vervangen door een configureerbaar vinkje op het operatietype
          ('Geen leverdefaults van leverancier'); de migratie zet dit vinkje
          automatisch op het Dropship-type. Datamigratie en Studio-opschoning
          via post_init_hook.
    """,
}
