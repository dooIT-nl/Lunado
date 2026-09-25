{
    "name": "Product & Partner Master Data",
    "summary": "Master data fields from Studio (ABC code, availability, cost calc, packing slip URL) and final Studio cleanup",
    "version": "19.0.1.0.7",
    "category": "Sales",
    "author": "dooIT B.V.",
    "website": "https://dooit.nl",
    "license": "LGPL-3",
    # Sluitstuk-module: hangt bewust op ALLE conversie-modules zodat de
    # eindschoonmaak (o.a. wees-veldrijen) gegarandeerd pas draait nadat de
    # andere modules hun x_studio-oudervelden hebben verwijderd.
    "depends": [
        "sale_stock",
        "mrp",
        "d1_handling_cost",
        "d1_sale_order_checks",
        "d1_sale_dropshipment",
        "d1_purchase_partner_delivery",
        "d1_sale_extra_service",
        "d1_sale_combi",
        "d1_mrp_sawing",
    ],
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

        * v1.0.7: definitieve fix Handling-modelverwijdering — modellen
          worden in een unlink met de uninstall-vlag verwijderd (Odoo's
          eigen cascade voor afhankelijke velden/delegaties, zoals bij het
          deinstalleren van studio_customization) i.p.v. veld-voor-veld;
          register wordt na (mislukte) verwijdering herladen en de
          view-deactivatie werkt per view met savepoint, zodat de
          installatie nooit meer afbreekt op 'Field x_active does not
          exist' (bevinding go-live-rehearsal 25-09)
        * v1.0.6: fix Handling-modelverwijdering — velden worden vooraf in
          meerdere passes verwijderd; de cascade blokkeerde op het
          related-veld x_currency_id dat op x_handling_id hangt (bevinding
          go-live-rehearsal 25-09). Herstelmigratie draait de opschoning
          opnieuw.
        * v1.0.5: eindschoonmaak verwijdert nu ook de handmatige
          Handling-modellen x_handling en x_handling_line_b0f2a inclusief
          hun velden, views en tabellen (data al gemigreerd door
          d1_handling_cost; besluit 25-09-2026 — de handmatige verwijderstap
          uit de deploy-checklist vervalt)
        * v1.0.4: eindschoonmaak verwijdert nu ook wees-veldrijen — de
          automatisch gedelegeerde x_studio-velden op product.product en
          res.users (_inherits) die als 'basisveld' achterbleven nadat het
          ouderveld was verwijderd. Levende registervelden (d1_studio_compat)
          en velden van x_handling-modellen blijven ongemoeid. Module hangt
          nu op alle conversie-modules (installatievolgorde). Herstelmigratie
          draait de veeg op bestaande databases.
        * 1.0.2-fix: robuustere Studio-opschoning + x_studio_handling opgeruimd + migratie die de opschoning opnieuw draait
        * v1.0.3: view-strip zonder modelfilter (embedded veld-verwijzingen);
          herstelmigratie draait de eindschoonmaak opnieuw
        * v1.0.1: productlijst-kolommen aantal verpakkingen en kostprijs calc (view-pariteit)
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
