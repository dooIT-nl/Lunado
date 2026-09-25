# d1_purchase_partner_delivery

Cluster **C3** van de Studio-conversie (zie `docs/studio_conversie_plan.md`).

## Functionaliteit

* Velden op de relatie (tabblad Verkoop & Inkoop, sectie Inkoop):
  **Delivery Operation Type** (Leveren aan) en **Delivery Incoterm**
  (Leverconditie).
* Bij het aanmaken van een inkooporder — of het wijzigen van de leverancier —
  worden beide waarden automatisch op de order gezet. Werkt in het formulier
  én bij API-creates.
* **Configureerbare uitsluiting:** vinkje *No Partner Delivery Defaults* op
  het operatietype (Voorraad → Configuratie → Operatietypes). Staat dat
  vinkje aan (bv. bij Dropship), dan worden de leverdefaults **niet**
  toegepast. Dit vervangt de hardcoded uitsluiting van operatietype id 10
  die verstopt zat in het filterdomein van de Studio-automation.

## Bewuste afwijkingen t.o.v. de Studio-automation

* Bevestigde/geannuleerde orders worden niet meer aangepast bij een
  leverancierswissel (voorheen wel — dat kon een bevestigde order stilletjes
  wijzigen).
* De incoterm wordt — net als voorheen — altijd mee overgenomen zodra de
  leverancier een leveroperatietype heeft, ook als de incoterm bij de
  leverancier leeg is.

## Migratie & Studio-opschoning (post_init_hook)

1. Data gekopieerd: `x_studio_type_levering` → `d1_delivery_picking_type_id`,
   `x_studio_incoterm_id` → `d1_incoterm_id`.
2. Vinkje automatisch gezet op het Dropship-operatietype
   (`stock_dropshipping.picking_type_dropship`, indien aanwezig).
3. Studio-automation *"Vul Leveren aan en Leverconditie"* verwijderd incl.
   server-actie; veldverwijzingen uit Studio-views geknipt; handmatige velden
   verwijderd (fouten worden gelogd, installatie blokkeert nooit).

Op een verse database doet de hook alleen stap 2.

## Contact

dooIT B.V. — https://dooit.nl
