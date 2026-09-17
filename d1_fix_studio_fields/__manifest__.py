{
    "name": "d1 Fix Studio Fields (deprecated)",
    "summary": "Stopgap for Studio computed fields — superseded by the Studio conversion modules; uninstall after deployment",
    "version": "19.0.1.0.1",
    "category": "Technical",
    "author": "dooIT B.V.",
    "website": "https://dooit.nl",
    "license": "LGPL-3",
    "depends": ["product"],
    "installable": True,
    "application": False,
    "description": """
        d1 Fix Studio Fields 19.0.1.0.1
        ===============================
        * v1.0.1: gemarkeerd als deprecated; license/summary toegevoegd.
          Deze module is vervangen door de Studio-conversie
          (d1_shipping_cost / d1_mrp_sawing). De map blijft in de repo
          totdat de module op ALLE databases (productie!) is gedeinstalleerd
          — een geinstalleerde module zonder code breekt de build.
          Deinstalleren via Apps na installatie van de conversie-modules;
          daarna mag de map definitief uit de repo.
        * v1.0: initiele versie (pleister voor Studio-computevelden).
    """,
}
