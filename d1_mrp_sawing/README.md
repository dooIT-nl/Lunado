# d1_mrp_sawing

Cluster **C6** van de Studio-conversie (zie `docs/studio_conversie_plan.md`) —
het zaag-/frame-/productietijd-maatwerk. Vervangt 7 Studio-automations en 18
Studio-velden, plus de pleister-module `d1_fix_studio_fields`.

## Functionaliteit

### Product (tabblad Voorraad, groep "Sawing")
* **Use Quantity / Use Length** — regels van dit product gebruiken een eigen
  hoeveelheid/lengte.
* **Saw Capacity per Operation** (stuks) en **Saw Time per Operation**
  (seconden).
* **Sawn Product Code**, **Frame Calculator**.
* Controles: *Gebruik Lengte vereist Gebruik Hoeveelheid*; zaagcapaciteit en
  zaagtijd moeten > 0 zijn voor producten met de **standaard
  productie-route** (besluit 17-09-2026: technische referentie i.p.v. de
  routenaam 'Productie').

### Verkooporderregel
* **Hoeveelheid × lengte → orderhoeveelheid** wordt verzorgd door de
  bestaande module **`d1_shipping_cost`** (afhankelijkheid): die bleek deze
  Studio-logica al te hebben geconverteerd, inclusief automatische
  lengte-vulling vanuit het product als 'Gebruik Lengte' uit staat.
  **Let op:** dit wijkt af van het besluit "letterlijk zoals nu"
  (17-09-2026) — de bestaande implementatie past de berekening alleen toe
  bij producten met 'Gebruik Hoeveelheid' (dus geen 0-hoeveelheden bij
  gewone producten). Twee concurrerende implementaties naast elkaar was
  geen optie; dit is gemeld bij oplevering.
* **Weight** = besteld aantal × productgewicht (berekend).
* **Frame ID** en berekend **Frame Number** (ordernummer zonder
  voorloop-'S' + '-' + laatste 3 tekens van het Frame ID).
* **Qty Var Name** (gevuld door externe koppeling).

### Productieorder
* **Sawing Quantity / Length / Frame Number** overgenomen van de gekoppelde
  verkoopregel (berekend, handmatig aanpasbaar voor MO's zonder
  verkoopkoppeling — kleine verbetering t.o.v. Studio).
* **Production Time** (minuten) = ⌈hoeveelheid ÷ zaagcapaciteit⌉ ×
  zaagtijd ÷ 60, afgerond op hele minuten.

### Werkorder & voorraadbewegingen
* Werkorders krijgen automatisch **verwachte én werkelijke duur** =
  productietijd (besluit 17-09-2026: huidig gedrag behouden; de werkelijke
  duur is daarmee fictieve tijdregistratie).
* Gerelateerde velden (hoeveelheid/lengte/productietijd) op werkorder en
  voorraadbeweging; optionele kolommen op de picking.

## Bewuste afwijkingen

* De velden `d1_use_qty`, `d1_use_length`, `d1_qty` en `d1_length` zijn
  eigendom van `d1_shipping_cost`; deze module voegt alleen de
  product-controles en de mrp-kant toe.
* De dode automation *"Vul lengte in verkooporderregel"* (code volledig
  uitgecommentarieerd) is vervallen en wordt door de migratie opgeruimd.
* De regel-route-toewijzing gebruikt Odoo 19's `route_ids`; zie ook
  `d1_sale_combi`.

## Migratie & Studio-opschoning (post_init_hook)

1. Data gekopieerd voor product- en orderregelvelden (productie/werkorder/
   voorraadvelden zijn berekend en hebben geen te migreren data).
2. `ir.default`-waarden voor zaagcapaciteit/zaagtijd overgezet naar de
   nieuwe velden.
3. De 7 Studio-automations verwijderd incl. server-acties;
   veldverwijzingen uit Studio-views geknipt; 24 handmatige velden
   verwijderd (fouten worden gelogd, installatie blokkeert nooit).

## Na installatie op productie

* Controleer of de module **`d1_fix_studio_fields`** nog geïnstalleerd is en
  deïnstalleer die (Apps → d1 Fix Studio Fields → Verwijderen); de module is
  uit de repository verwijderd.

## Contact

dooIT B.V. — https://dooit.nl
