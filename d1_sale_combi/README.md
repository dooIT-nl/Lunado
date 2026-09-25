# d1_sale_combi

Cluster **C5** van de Studio-conversie (zie `docs/studio_conversie_plan.md`).

## Functionaliteit

* **Combi**-vlag op de verkooporder (naast het magazijn).
* **Default Warehouse** op het product (tabblad Voorraad): het magazijn
  waaruit het product normaal geleverd wordt.
* **Combi Route** op het magazijn (Voorraad → Configuratie → Magazijnen):
  de route die combi-regels krijgen.

Bij een combi-order (offerte-status) geldt per regel met een fysiek product:

1. Geen standaard magazijn op het product → **foutmelding**.
2. Standaard magazijn ≠ ordermagazijn → regel krijgt de **combi-route van
   het ordermagazijn**; heeft dat magazijn geen combi-route → foutmelding
   ("combi nog niet actief").
3. Standaard magazijn = ordermagazijn → regel blijft ongemoeid.

Toegepast bij aanmaken van order/regels, bij productwijziging en bij het
(aan)zetten van de combi-vlag of wisselen van magazijn — UI én API.

## Configuratie na installatie

De migratie koppelt automatisch (met naam-controle als vangnet):
Rotterdam → *Combi RTM: Lever in 3 stappen*, Wesseling → *Combi WLS: Lever
in 3 stappen* — de mapping die voorheen hardcoded (magazijn-id 1/2 →
route-id 21/22) in de Studio-automations zat. Nieuwe magazijnen activeer je
door simpelweg een Combi Route in te stellen; er is geen code-aanpassing
meer nodig (voorheen: foutmelding "nog niet actief" vanuit hardcoded ids).

## Bewuste afwijkingen t.o.v. de Studio-automations

* Alleen actief in offerte-status (voorheen ook op bevestigde orders bij
  veldwijzigingen).
* Productfilter is `type = 'consu'` (goederen); het oude filter
  `['consu','product']` stamde uit een oudere Odoo-versie waarin 'product'
  nog een producttype was.
* Routes worden niet teruggezet als de combi-vlag weer uitgaat (pariteit met
  de oude automation).

## Migratie & Studio-opschoning (post_init_hook)

1. Data gekopieerd: `x_studio_default_warehouse_id` →
   `d1_default_warehouse_id` (product), `x_studio_combi` → `d1_combi`.
2. Combi-routes per magazijn gevuld (zie hierboven).
3. Beide Studio-automations *Combi order* verwijderd incl. server-acties;
   veldverwijzingen uit Studio-views geknipt; handmatige velden verwijderd
   (fouten worden gelogd, installatie blokkeert nooit).

## Contact

dooIT B.V. — https://dooit.nl
