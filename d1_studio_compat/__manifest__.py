{
    "name": "Studio Field Compatibility (deprecated)",
    "summary": "Temporary aliases exposing the old x_studio_* field names to external integrations; uninstall once the integration uses the d1_ names",
    "version": "19.0.1.0.1",
    "category": "Technical",
    "author": "dooIT B.V.",
    "website": "https://dooit.nl",
    "license": "LGPL-3",
    "depends": [
        "d1_sale_order_checks",
        "d1_sale_dropshipment",
        "d1_purchase_partner_delivery",
        "d1_sale_combi",
        "d1_mrp_sawing",
        "d1_product_partner_data",
        "d1_handling_cost",
    ],
    "installable": True,
    "application": False,
    "description": """
        Studio Field Compatibility 19.0.1.0.0
        =====================================
        TIJDELIJKE overgangsmodule bij de Studio-conversie
        (zie docs/studio_conversie_plan.md).

        * v1.0.1: alias x_studio_artikelcode_gezaagd volgt de hernoeming naar
          d1_raw_product_id (CIS20260922)
        * v1.0: alias-velden met de oude x_studio_*-namen, gedelegeerd naar
          de nieuwe d1-velden, zodat externe koppelingen (json2 API) blijven
          werken totdat ze zijn omgezet naar de nieuwe veldnamen.
          LET OP: pas installeren nadat alle conversie-modules (incl.
          herstelmigraties) volledig zijn doorgevoerd — een achtergebleven
          handmatig x_studio-veld met dezelfde naam conflicteert met deze
          aliassen. Deinstalleren zodra de koppeling is omgezet.
    """,
}
