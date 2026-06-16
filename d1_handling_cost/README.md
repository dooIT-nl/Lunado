# d1_handling_cost — Handling Cost

**Auteur:** dooIT B.V.  
**Versie:** 19.0.1.0.0  
**Licentie:** LGPL-3

## Doel

Vervangt de Studio-modellen `x_handling` en `x_handling_line_b0f2a` door schone
`d1.handling` / `d1.handling.line`-modellen met bijbehorende views, menu,
toegangsrechten en een automatische handling-kostenregel op offertes.

## Installatie

```bash
odoo-bin -i d1_handling_cost --stop-after-init --no-http
```

Bij installatie worden bestaande records uit de Studio-modellen automatisch
gemigreerd via een `post_init_hook`.

## Functionaliteit

- **d1.handling** — Handling-configuratie met staffelregels (cost brackets).
- **d1.handling.line** — Individuele staffelregel (van/tot bedrag → kosten).
- **res.partner** — Veld `d1_handling_id` (Many2one → d1.handling).
- **Automatisering** — "d1 Sale: Add Handling": voegt automatisch een
  handling-kostenregel toe, werkt deze bij of verwijdert deze op basis van de
  klant-handling en het orderbedrag bij aanmaken/wijzigen van een offerte.

## Menu

Verkoop → Catalogus → Handling

## OPEN PUNTEN / NA INSTALLATIE

1. **Migratie verifiëren op staging** — Controleer dat aantallen kloppen:
   aantal d1.handling-records = aantal oude x_handling-records, koppelingen
   partner → handling correct.

2. **Oude Studio-velden/-modellen NIET verwijderen** — De modellen `x_handling`,
   `x_handling_line_b0f2a` en het veld `x_studio_handling` op `res.partner`
   worden in een **aparte, latere opruimactie** verwijderd — niet door deze
   module.

3. **Config-parameter `d1_handling_cost.shipping_product_id`** — Na installatie
   moet hier het product.template-ID van het legacy DeliveryMatch
   shipping-product worden ingevuld. Zolang dit niet is geconfigureerd, telt
   dat product mee in het handling-basisbedrag (kan leiden tot een verkeerd
   staffelbedrag). **OPEN PUNT**.

4. **Overige Studio-automatiseringen** — De automatiseringen voor
   product/purchase/sale horen bij andere modules en worden niet door deze
   module behandeld.

## Tests

```bash
odoo-bin --test-tags d1_handling_cost -u d1_handling_cost --stop-after-init --no-http
```
