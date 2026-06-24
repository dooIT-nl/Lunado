{
    "name": "Handling Cost",
    "summary": "Clean handling cost models replacing Studio x_handling, with automated order line sync",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "author": "dooIT B.V.",
    "website": "https://dooit.nl",
    "license": "LGPL-3",
    "depends": [
        "sale_management","contacts",
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
        Handling Cost 19.0.1.0.0
        ========================
        * v1.0.0: initial release — d1.handling / d1.handling.line models,
          partner link, automated handling line on draft sale orders,
          post_init_hook migration from Studio x_handling data.
    """,
}
