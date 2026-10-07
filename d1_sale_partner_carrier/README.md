# d1_sale_partner_carrier — Default Carrier from Customer

## Doel

De leveringswijze (`carrier_id`) op de verkooporder wordt bij het aanmaken
van een offerte automatisch voorgevuld met de standaard leveringswijze van
de klant (veld **Leveringswijze** / `property_delivery_carrier_id` op de
contactkaart, tabblad Verkoop & Inkoop). Dit werkt voor alle kanalen: de
Odoo-UI én API-creates (bv. de Conneo-koppeling).

## Waarom dit niet standaard gebeurt

Standaard laat Odoo `carrier_id` leeg bij het aanmaken. De voorkeur van de
klant wordt alleen gebruikt als **default in de wizard "Verzendkosten
toevoegen"** (`action_open_delivery_wizard`): daar wordt hij ook getoetst op
beschikbaarheid voor het afleveradres. Odoo stelt de keuze dus bewust uit
tot het moment van berekenen. Deze module vult het veld alvast in, zodat de
leveringswijze direct zichtbaar en via de API gevuld is.

## Gedrag

* Bij aanmaken/wijzigen van het **afleveradres**: standaard leveringswijze
  van dat adres, met terugval op de commerciele partner (zelfde logica als
  de standaard wizard). Alleen actieve carriers.
* Alleen op openstaande offertes (concept/verzonden); na bevestiging wijzigt
  er niets meer automatisch.
* Handmatig aanpassen blijft mogelijk; de keuze blijft staan totdat het
  afleveradres opnieuw wijzigt en wordt nooit automatisch leeggemaakt.
* De wizard **Verzendkosten toevoegen/berekenen** blijft leidend: bij
  bevestigen schrijft die (standaardgedrag) de gekozen leveringswijze en de
  kostenregel naar de order.

## Bekende beperkingen

* De voorgevulde waarde wordt niet getoetst op land-/gewichtsrestricties van
  de carrier (dat doet de wizard alsnog bij het berekenen).

## Contact

dooIT B.V. — https://dooit.nl
