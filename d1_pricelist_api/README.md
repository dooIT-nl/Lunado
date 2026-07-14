# d1_pricelist_api — Pricelist Price API

## Doel

Odoo 19 stelt de interne prijslijstberekening (`_get_products_price` e.d. op
`product.pricelist`) niet beschikbaar via de externe API: alle
berekeningsmethodes zijn private (underscore-prefix) en geven een
403 FORBIDDEN via de JSON-2 API. Deze module voegt één publieke
wrapper-methode toe die de interne berekening ontsluit voor externe systemen,
zoals een webshop.

- **Endpoint:** `POST {host}/json/2/product.pricelist/d1_api_get_customer_price`
- **Body:** `{"partner_id": <int>, "product_id": <int>, "quantity": <float>}`
- **Retour:** JSON-object met o.a. `price` (excl. btw), `pricelist_id`,
  `pricelist_name`, `currency`.

De prijslijst wordt server-side bepaald via de klant
(`res.partner.property_product_pricelist`); de aanroeper hoeft geen
prijslijst-ID te kennen. Staffelprijzen worden meegenomen via `quantity`.

## Installatie

1. Plaats deze module in de addons-map van de Odoo.sh-repo en push naar de
   gewenste branch (zie CLAUDE.md sectie 13).
2. Activeer developer mode → Apps → *Update Apps List*.
3. Installeer **Pricelist Price API**.

## Gebruik / autorisatie

De aanroepende API-gebruiker (bearer API-key) heeft leesrechten nodig op
`res.partner`, `product.product` en `product.pricelist`. Toegangsrechten van
Odoo blijven onverkort gelden; de module omzeilt geen security (geen
`sudo()`).

Voorbeeld-aanroep en testscript: zie `test_pricelist_api.py` in de
documentatie-repo (PyCharm-script) of het integratiedocument
"Lunado — Integratie met Odoo ERP via de API".

## Bekende beperkingen

- Prijs is **exclusief btw**; btw-berekening is bewust buiten scope.
- Eén product per aanroep (geen bulk-variant).
- Geen expliciete prijslijst-parameter; altijd de prijslijst van de klant.

## Opmerkingen

- `security/ir.model.access.csv` bevat alleen de header: de module
  introduceert geen nieuwe modellen, er zijn dus geen access-regels nodig.
  Het bestand is aanwezig conform CLAUDE.md sectie 6.
- `static/description/icon.png` is een placeholder — vervangen door het
  dooIT-logo vóór productie-merge.

## Contact

dooIT B.V. — https://dooit.nl
Contactpersoon: Rene
