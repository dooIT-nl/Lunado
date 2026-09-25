# d1_sale_extra_service

Cluster **C4** van de Studio-conversie (zie `docs/studio_conversie_plan.md`).

## Functionaliteit

* Veld **Extra Service** op de productcategorie: een dienst-artikel dat
  automatisch aan verkooporders wordt toegevoegd zodra de order producten
  uit die categorie bevat.
* De hoeveelheid van de dienstregel = **som van de zaaghoeveelheden**
  (`d1_qty`, uit `d1_shipping_cost`) van de betreffende regels, en wordt
  automatisch bijgewerkt bij wijzigingen.
* Alleen voor orders **zonder bronndocument** (origin) in offerte-status —
  pariteit met het filterdomein van de Studio-automation.
* Dienstregels worden niet verwijderd als de som 0 wordt (pariteit).

## Bewuste afwijkingen

* **Sommering per dienst-artikel**: de Studio-versie telde de hoeveelheden
  van regels met *verschillende* diensten bij elkaar op (bug); nu wordt per
  dienst-artikel gesommeerd — het gedocumenteerde doel van de automation.
* Alleen actief in offerte-status.

## Migratie & Studio-opschoning (post_init_hook)

1. Data gekopieerd: `product.category.x_studio_extra_dienst` →
   `d1_extra_service_product_id`.
2. Studio-automation *"Verkooporderregel: Voeg dienst toe"* verwijderd incl.
   server-actie; veldverwijzing uit de Studio-categorieviews geknipt;
   handmatig veld verwijderd (fouten worden gelogd, installatie blokkeert
   nooit).

## Contact

dooIT B.V. — https://dooit.nl
