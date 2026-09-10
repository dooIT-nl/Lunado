# d1_sale_commitment_date

Berekent de leverdatum (`commitment_date`) van een verkooporder automatisch op
basis van de orderregels, zolang de order in offerte-status is (concept /
verzonden).

## Berekening per orderregel

1. **Voldoende vrije voorraad** (`free_qty` in het magazijn van de order):
   levering is direct mogelijk — de `sale_delay` van het product wordt
   genegeerd.
2. **Onvoldoende voorraad**: de `scheduled_date` van de **eerstvolgende
   geplande ontvangst** (inkomende `stock.picking`, niet gereed/geannuleerd)
   met dit product wordt gebruikt.
3. **Geen geplande ontvangst**: vandaag + `sale_delay` van het product.

**Per order:** de laatste berekende regeldatum = eerst mogelijke leverdatum
(uitgangspunt: geen deelleveringen).

## Kit-/productieartikelen

Heeft het product een stuklijst van het type *kit* of *produceer dit product*,
dan worden de stuklijstregels als orderregels behandeld. Benodigd aantal per
component = aantal stuklijstregel x aantal op de orderregel (bewust **niet**
gedeeld door het aantal van de stuklijst-header, conform specificatie). De
componenten volgen daarna dezelfde berekening als reguliere regels.

## Gewenste leverdatum klant

Extra veld **Customer Requested Date** op de orderheader:

* Is de gewenste datum **later** dan de berekende datum, dan wordt de gewenste
  datum overgenomen als leverdatum.
* Is de gewenste datum **eerder** dan de berekende datum, dan blijft de
  berekende datum staan en toont het formulier een waarschuwingsbanner.

## Bekende beperkingen

* Voorraad wordt per regel/component beoordeeld, niet cumulatief over de hele
  order (twee regels met hetzelfde product "delen" dus dezelfde vrije
  voorraad).
* Stuklijsten worden 1 niveau diep geexplodeerd (geen geneste stuklijsten).
* Bevestigde orders worden niet meer herberekend.
* Geen nieuwe modellen; daarom bevat de module geen `ir.model.access.csv`.

## Installatie

Standaard installatie via Apps (`d1_sale_commitment_date`). Afhankelijk van
`sale_stock` en `mrp`.

## Contact

dooIT B.V. — https://dooit.nl
