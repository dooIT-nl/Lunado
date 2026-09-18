{
    "name": "MRP Sawing",
    "summary": "Sawing quantities, lengths, frames and production time on sales, manufacturing and stock (replaces Studio customizations)",
    "version": "19.0.1.0.4",
    "category": "Manufacturing",
    "author": "dooIT B.V.",
    "website": "https://dooit.nl",
    "license": "LGPL-3",
    "depends": ["sale_stock", "mrp", "d1_shipping_cost"],
    "data": [
        "views/product_template_views.xml",
        "views/sale_order_views.xml",
        "views/mrp_production_views.xml",
        "views/mrp_workorder_views.xml",
        "views/stock_picking_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "description": """
        MRP Sawing 19.0.1.0.4
        =====================
        Cluster C6 van de Studio-conversie (zie docs/studio_conversie_plan.md).

        * v1.0.4: veld-opschoning in meerdere passes (afhankelijkheidsketens
          zoals stock.move -> orderregel) en zonder tracebacks in het log;
          migratie draait de opschoning opnieuw
        * v1.0.3: robuustere Studio-opschoning (views met veld-verwijzingen
          in attributen worden gedeactiveerd) + herstelmigratie
        * v1.0.2: view-pariteit met Studio hersteld (werkorderformulier,
          productlijst-kolommen, qty-var-name op de orderregel)
        * v1.0.1: velden op de productieorder op de oorspronkelijke
          Studio-plekken gezet (naast Verantwoordelijke; productietijd in de
          componentenlijst; hoeveelheid/lengte in de werkorderlijst en
          zichtbaar op de picking)
        * v1.0: initiele versie — vervangt 7 Studio-automations en 18
          Studio-velden rond zagen/lengtes/frames. Product: gebruik
          hoeveelheid/lengte, zaagcapaciteit en -tijd, artikelcode gezaagd,
          framecalculator, controles. Orderregel: hoeveelheid x lengte,
          gewicht, frame-id/-nummer. Productieorder: waarden vanuit de
          verkoopregel plus productietijd (zaagformule). Werkorder:
          verwachte en werkelijke duur automatisch gevuld; gerelateerde
          velden op werkorder en voorraadbewegingen. Route-check gekoppeld
          aan de standaard productie-route. Vervangt tevens de
          pleister-module d1_fix_studio_fields. Datamigratie en
          Studio-opschoning via post_init_hook.
    """,
}
