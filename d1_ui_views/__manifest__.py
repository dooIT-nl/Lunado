{
    "name": "UI View Tweaks (Studio Parity)",
    "summary": "Optional list columns on standard fields, ported from the Studio view customizations",
    "version": "19.0.1.0.0",
    "category": "Hidden",
    "author": "dooIT B.V.",
    "website": "https://dooit.nl",
    "license": "LGPL-3",
    "depends": ["sale_stock"],
    "data": [
        "views/ui_views.xml",
    ],
    "installable": True,
    "application": False,
    "description": """
        UI View Tweaks (Studio Parity) 19.0.1.0.0
        =========================================
        Onderdeel van de Studio-conversie (zie docs/studio_conversie_plan.md,
        view-pariteitsslag).

        * v1.0: optionele lijstkolommen op standaardvelden, geport uit de
          Studio-lijstviews: product (voorraad bijhouden), verkooporders
          (bron), locaties (magazijn, retour/afval, waarderingsrekeningen)
          en routes (toepasbaarheidsvlaggen). Bewust niet geport:
          Studio-views op technische modellen, metadata-kolommen
          (id/aanmaakdatum e.d.) en de boekhoudkolommen op de
          productcategorielijst — zie de conversieplan-notities.
    """,
}
