# d1_sale_dropshipment

Cluster **C2** van de Studio-conversie (zie `docs/studio_conversie_plan.md`).

## Functionaliteit

* **Dropshipment**-vlag op de relatie (tabblad Verkoop & Inkoop).
* Dezelfde vlag op de verkooporder, **automatisch overgenomen van de klant**
  zodra de klant wordt gezet of gewijzigd — geïmplementeerd als stored
  compute (`readonly=False`), waardoor het werkt voor **alle kanalen**
  (formulier én API-creates) en **alle gebruikers**. Handmatig aanpassen per
  order blijft mogelijk.

## Waarom dit 2 Studio-automations vervangt

In Studio waren twee automations nodig: een `on_change`-variant voor het
formulier en een `on_create_or_write`-variant (beperkt tot de API-gebruikers)
omdat onchange-logica niet draait bij API-creates. Een stored compute dekt
beide gevallen in één implementatie; de hardcoded gebruikersfilter
(id 11/13) is daarmee vervallen (besluit 17-09-2026: de regel geldt altijd en
voor iedereen).

## Migratie & Studio-opschoning (post_init_hook)

1. Data gekopieerd: `x_studio_dropshipment` → `d1_dropshipment` (partner en
   order).
2. Beide Studio-automations *"Verkooporder: Dropshipment overnemen van
   klantgegevens"* verwijderd, inclusief server-acties.
3. Veldverwijzingen uit Studio-views geknipt, daarna de handmatige velden
   verwijderd (fouten worden gelogd, installatie blokkeert nooit).

Op een verse database doet de hook niets.

## Contact

dooIT B.V. — https://dooit.nl
