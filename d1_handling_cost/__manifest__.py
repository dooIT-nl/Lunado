{
    "name": "Handling Cost",
    "summary": "Clean handling cost models replacing Studio x_handling, with automated order line sync",
    "version": "19.0.1.0.2",
    "category": "Sales",
    "author": "dooIT B.V.",
    "website": "https://dooit.nl",
    "license": "LGPL-3",
    "depends": [
        "sale_management",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/d1_handling_views.xml",
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "application": False,
    "post_init_hook": "_post_init_migrate_handling",
    "description": """
        Handling Cost 19.0.1.0.2
        ========================
        * v1.0.2: handling wordt nu ook toegepast bij het aanmaken van een
          order (create-override) en bij losse regelwijzigingen
          (create/write/unlink op de orderregel) — voorheen alleen bij een
          order-write, waardoor orders met enkel reguliere artikelen geen
          handlingregel kregen
        * v1.0.1: optionele handlingkolom op de partnerlijst (view-pariteit)
        * v1.0.0: initial release — d1.handling / d1.handling.line models,
          partner link, automated handling line on draft sale orders,
          post_init_hook migration from Studio x_handling data.
    """,
}
