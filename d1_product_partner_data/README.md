# d1_product_partner_data

Cluster **C7** — het **sluitstuk** van de Studio-conversie
(zie `docs/studio_conversie_plan.md`).

## Functionaliteit

### Product (Algemene informatie)
* **ABC Code** (04/05/06/07), **Courant**, **Calculated Cost**.
* **Available** (berekend): voorraad > 0, behalve bij een
  subcontract-stuklijst — herbouwd *zoals bedoeld* (besluit 17-09-2026);
  de Studio-versie liet producten zonder voorraad en zonder stuklijst hun
  oude waarde behouden.
* **Packaging Count** (berekend): aantal verpakkings-UoM's — in Odoo 19
  zijn productverpakkingen opgegaan in UoM's (`uom_ids`).

### Verkooporder
* **Packing Slip URL** (gevuld door de externe koppeling), klikbaar en
  alleen zichtbaar als gevuld.

### KvK-nummer
* `x_studio_coc` is **gemigreerd naar het standaardveld
  `company_registry`** (besluit 17-09-2026); bestaande waarden in
  `company_registry` worden niet overschreven. Er is geen apart d1-veld.

## Eindschoonmaak (post_init_hook)

Naast de datamigratie en veldopschoning voert dit cluster de laatste veeg
van de conversie uit:

1. Studio-automation *"Verkoop: Voeg Handling toe"* verwijderd (functioneel
   vervangen door `d1_handling_cost` — daarom een afhankelijkheid, zodat de
   handling-datamigratie altijd eerder draait).
2. Het Studio-**Handling-menu** en de bijbehorende vensteractie verwijderd.
3. **Alle resterende `studio_customization`-views gedeactiveerd** (bewust
   niet verwijderd): de consultant kan ze op staging nalopen en gewenste
   lay-out alsnog als module-view laten porten.

## Handmatige nazorg op productie (na verificatie)

* De lege Studio-modellen `x_handling` / `x_handling_line_b0f2a` (data is
  door `d1_handling_cost` gemigreerd) kunnen daarna handmatig verwijderd
  worden (Instellingen → Technisch → Modellen), inclusief hun
  toegangsrechten.
* Controleer de gedeactiveerde Studio-views en verwijder ze definitief als
  er niets meer uit nodig is.

## Contact

dooIT B.V. — https://dooit.nl
