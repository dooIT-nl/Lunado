{
    "name": "Sale Order Checks",
    "summary": "Credit limit, prospect and duplicate customer reference checks on sale orders (replaces Studio automations)",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "author": "dooIT B.V.",
    "website": "https://dooit.nl",
    "license": "LGPL-3",
    "depends": ["sale_management"],
    "data": [
        "views/res_partner_views.xml",
        "views/sale_order_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "description": """
        Sale Order Checks 19.0.1.0.0
        ============================
        Cluster C1 van de Studio-conversie (zie docs/studio_conversie_plan.md).

        * v1.0: initiele versie — vervangt de Studio-automations
          'Kredietlimiet', 'Relatie is Prospect' en 'Verkooporder: Dubbele
          referentie' (2x) door Python-checks. Velden hernoemd:
          x_studio_rel_type -> d1_rel_type,
          x_studio_kredietverzekering -> d1_credit_insurance,
          x_studio_verzekerd_bedrag -> d1_insured_amount,
          x_studio_credit_limit_exceeded -> d1_credit_limit_exceeded,
          x_studio_exceed_credit_limit -> d1_exceed_credit_limit.
          Datamigratie en Studio-opschoning via post_init_hook.
          Dubbele-referentiecheck geldt nu voor alle gebruikers (besluit
          17-09-2026); prospect-blokkade gedraagt zich exact als voorheen.
    """,
}
