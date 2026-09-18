{
    "name": "Sale Commitment Date from Order Lines",
    "summary": "Compute the sale order delivery date from stock, incoming receipts and customer lead time",
    "version": "19.0.1.2.1",
    "category": "Sales",
    "author": "dooIT B.V.",
    "website": "https://dooit.nl",
    "license": "LGPL-3",
    "depends": ["sale_stock", "mrp"],
    "data": [
        "data/ir_config_parameter_data.xml",
        "views/res_partner_views.xml",
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "application": False,
    "description": """
        Sale Commitment Date from Order Lines 19.0.1.2.0
        ================================================
        * v1.2.1: standaardmelding 'Gevraagde datum is te snel' onderdrukt
          zolang de module de leverdatum berekent (expected_date telt
          sale_delay mee en spreekt de berekening onterecht tegen)
        * v1.2: klantbesluiten LUN verwerkt — voorraadbegrip = fysieke
          voorraad minus alle bevestigde uitgaande vraag; ontvangsten in het
          verleden afgetopt op vandaag; leverdatum afgerond op werkdagen met
          per-klant instelbare cutoff-tijd (default via systeemparameter)
        * v1.1: vertalingen toegevoegd (nl_NL, de_DE) voor velden, helpteksten
          en waarschuwingsbanner; bannertekst herschreven voor schone
          vertaaltermen
        * v1.0.1: velden met eigen label in de Delivery-sectie geplaatst
          (stonden labelloos in de Delivery Date-rij en waren onzichtbaar)
        * v1.0: initiele versie — berekening commitment_date per orderregel
          (vrije voorraad / eerstvolgende ontvangst / sale_delay), stuklijst-
          explosie voor kit- en productieartikelen, gewenste leverdatum klant
          met waarschuwingsbanner.
    """,
}
