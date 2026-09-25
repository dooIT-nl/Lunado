{
    "name": "Framecalculator",
    "summary": "Open the external frame calculator from the sale order, with configurable URL and API key (replaces a manual server action)",
    "version": "19.0.1.0.1",
    "category": "Sales",
    "author": "dooIT B.V.",
    "website": "https://dooit.nl",
    "license": "LGPL-3",
    "depends": ["sale_management"],
    "data": [
        "views/res_config_settings_views.xml",
        "views/sale_order_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "description": """
        Framecalculator 19.0.1.0.0
        ==========================
        * v1.0.1: kortere labels in de instellingen ('URL' en 'API-key' —
          het kopje zegt al Framecalculator)
        * v1.0: initiele versie — knop 'Framecalculator' op de verkooporder
          (naast Voorbeeld) die de externe framecalculator opent met orderid
          en customerid. URL en API-key zijn instelbaar via Verkoop >
          Instellingen > Framecalculator (systeemparameters) in plaats van
          hardcoded in een serveractie. De migratie neemt de bestaande
          waarden over uit de oude handmatige serveractie en verwijdert die.
    """,
}
