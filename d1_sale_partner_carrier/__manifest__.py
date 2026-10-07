{
    "name": "Default Carrier from Customer",
    "summary": "Prefill the sale order delivery method from the customer's preferred carrier on creation (UI and API)",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "author": "dooIT B.V.",
    "website": "https://dooit.nl",
    "license": "LGPL-3",
    "depends": ["delivery"],
    "data": [],
    "installable": True,
    "application": False,
    "description": """
        Default Carrier from Customer 19.0.1.0.0
        ========================================
        * v1.0: initiele versie — de leveringswijze (carrier_id) op de
          verkooporder wordt bij aanmaken voorgevuld met de standaard
          leveringswijze van het afleveradres (veld 'Leveringswijze' op de
          klant), met terugval op de commerciele partner. Werkt voor alle
          kanalen (UI en API-creates). Handmatig wijzigen per order blijft
          mogelijk; de wizard 'Verzendkosten toevoegen/berekenen' blijft
          leidend en overschrijft de waarde met de gekozen berekening
          (standaardgedrag, ongewijzigd).
    """,
}
