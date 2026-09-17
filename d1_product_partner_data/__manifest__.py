{
    "name": "Product & Partner Master Data",
    "summary": "Master data fields from Studio (ABC code, availability, cost calc, packing slip URL) and final Studio cleanup",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "author": "dooIT B.V.",
    "website": "https://dooit.nl",
    "license": "LGPL-3",
    "depends": ["sale_stock", "mrp", "d1_handling_cost"],
    "data": [
        "views/product_template_views.xml",
        "views/sale_order_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "description": """
        Product & Partner Master Data 19.0.1.0.0
        ========================================
        Cluster C7 (sluitstuk) van de Studio-conversie
        (zie docs/studio_conversie_plan.md).

        * v1.0: initiele versie — stamdatavelden hernoemd:
          x_studio_abc_code -> d1_abc_code,
          x_studio_courant -> d1_courant,
          x_studio_available -> d1_available (bug gefixt: nu consistent
          voorraad > 0, behalve bij subcontract-stuklijst — besluit
          17-09-2026),
          x_studio_aantal_verpakkingen -> d1_package_count (Odoo 19:
          verpakkingen zijn uom_ids),
          x_studio_kostprijs_calc -> d1_cost_calc,
          x_studio_url_pakbon -> d1_delivery_note_url.
          x_studio_coc (KvK) gemigreerd naar standaardveld company_registry
          (besluit 17-09-2026). Eindschoonmaak: Studio-automation 'Verkoop:
          Voeg Handling toe' (vervangen door d1_handling_cost), het
          Handling-menu en alle resterende Studio-views (gedeactiveerd, niet
          verwijderd).
    """,
}
