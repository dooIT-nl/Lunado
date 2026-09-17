# d1_sale_order_checks

Cluster **C1** van de Studio-conversie (zie `docs/studio_conversie_plan.md`).
Vervangt vier Studio-automations door versioned, geteste Python-checks.

## Functionaliteit

### Kredietlimiet
* Nieuw veld op de order: **Allow Exceeding Credit Limit** (alleen zichtbaar
  als de limiet is overschreden).
* Indicator **Credit Limit Exceeded** (berekend, niet opgeslagen — altijd
  actueel): openstaand saldo van de factuurklant > kredietlimiet (> 0).
* **Bevestigen wordt geblokkeerd** met een foutmelding zolang de limiet is
  overschreden en het vinkje niet is gezet. Rode banner op het formulier.

### Prospect-blokkade
* Nieuw veld op de relatie: **Relation Type** (Prospect / Customer).
* Verkooporders (ook offertes) voor relaties van het type *Prospect* worden
  geblokkeerd — exact het oude Studio-gedrag (besluit 17-09-2026).

### Dubbele klantreferentie
* Een klantreferentie die al op een andere order van dezelfde klant staat
  wordt **voor alle gebruikers** geblokkeerd bij opslaan (besluit 17-09-2026;
  voorheen alleen voor de API-gebruikers), plus een niet-blokkerende melding
  direct bij het invoeren.

### Kredietverzekering (informatief)
* Velden op de relatie: **Credit Insurance** (verzekerd eigen beoordeling /
  verzekerd beoordeling verzekeraar / niet verzekerd) en **Insured Amount**.

## Migratie & Studio-opschoning (post_init_hook)

Bij installatie op een database mét Studio-data (productie):

1. Data wordt gekopieerd: `x_studio_rel_type` → `d1_rel_type` (waarden
   vertaald naar keys), `x_studio_kredietverzekering` → `d1_credit_insurance`,
   `x_studio_verzekerd_bedrag` → `d1_insured_amount`,
   `x_studio_exceed_credit_limit` → `d1_exceed_credit_limit`.
2. De Studio-automations *Kredietlimiet*, *Relatie is Prospect* en
   *Verkooporder: Dubbele referentie* (2×) worden verwijderd, inclusief hun
   server-acties.
3. Verwijzingen naar de vervangen velden worden uit de Studio-views geknipt,
   daarna worden de handmatige velden verwijderd. Lukt dat ergens niet, dan
   wordt dat gelogd en overgeslagen (installatie blokkeert nooit).

Op een verse database (development/staging zonder Studio-kolommen) doet de
hook niets — veilig her-installeerbaar.

## Bewuste afwijkingen

* `d1_insured_amount` is `Float` i.p.v. `Monetary`: res.partner heeft geen
  currency-veld en het bronveld was ook Float (bedrag in bedrijfsvaluta).
* Geen `ir.model.access.csv`: geen nieuwe modellen.

## Contact

dooIT B.V. — https://dooit.nl
