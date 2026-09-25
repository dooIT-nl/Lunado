# Conversieplan Studio-aanpassingen → dooIT-modules (Lunado)

| | |
|---|---|
| Bron | Productie-export `studio_export_lunado_main_20260917.pydata` (17 sep 2026) |
| Omvang | 3 modellen, 61 velden, 34 views, 18 automations, 18 server-acties, 6 defaults |
| Doel | Alle Studio-maatwerk als versioned `d1_`-modules, x_studio-velden hernoemd naar `d1_` met datamigratie, Studio-onderdelen automatisch opgeruimd |
| Aanpak | Gefaseerd per functioneel cluster (besluit 17 sep 2026) |
| **Status** | **✅ Alle clusters C1–C7 opgeleverd op `development` (17 sep 2026)** — zie statusoverzicht onderaan |

---

## 1. Wat NIET geconverteerd wordt

| Onderdeel | Reden |
|---|---|
| `x_res_partner_private` (+ 2 velden) | Door Odoo zelf aangemaakt (privé-adressen HR), geen Studio-maatwerk |
| `account.analytic.line.x_plan2_id` / `x_plan3_id` | Door Odoo aangemaakt (analytische plannen), beheerd door standaard |
| Automation *"Vul lengte in verkooporderregel"* | Code is volledig uitgecommentarieerd — vervallen (bevestigen) |
| `x_handling` + regels + menu + views + automation *"Voeg Handling toe"* | **Al vervangen door `d1_handling_cost`** — alleen pariteit verifiëren + opschoning in migratie |
| Lijst-views op technische modellen (`base.automation`, `ir.ui.view`, `ir.actions.server`, `res.users`, `account.account`) | Ontwikkelaars-gemak, geen businesswaarde — laten vervallen (bevestigen) |
| `x_studio_coc` (KvK-nummer, res.partner) | Standaardveld `company_registry` bestaat in 19 — data migreren naar standaard, veld vervalt (bevestigen) |

## 2. Clusterindeling (voorgestelde modules)

### C1. `d1_sale_order_checks` — verkoopordercontroles *(klein, start hier)*
* **Velden:** partner `d1_rel_type` (Prospect/Klant), `d1_kredietverzekering`, `d1_verzekerd_bedrag`; order `d1_credit_limit_exceeded` (compute), `d1_exceed_credit_limit`
* **Logica (nu 5 automations):** kredietlimiet-blokkade bij bevestigen; prospect-waarschuwing bij klantkeuze; dubbele klantreferentie-check (2 Studio-varianten → 1 implementatie via constraint + onchange)
* **Aandachtspunt:** user-filter `env.user.id in [11,13]` (API-user/Conneo) → configureerbaar maken

### C2. `d1_sale_dropshipment` — dropshipment-vlag
* Partner + order boolean, overnemen van klant bij aanmaken/wijzigen (2 automations → compute/onchange)
* Zelfde hardcoded users [11,13] → zelfde configuratie als C1

### C3. `d1_purchase_partner_delivery` — leverdefaults inkoop
* Partner `d1_type_levering` (picking type) + `d1_incoterm_id` → automatisch op inkooporder
* **Aandachtspunt:** domein `picking_type_id != "10"` (hardcoded, als string!) → logica herzien met consultant

### C4. `d1_sale_extra_service` — extra dienst per productcategorie
* `product.category.d1_extra_service_product_id`; bij orderregels met hoeveelheid wordt het dienst-artikel automatisch toegevoegd/gesommeerd
* Afhankelijk van C6-veld `d1_qty` (leveringsvolgorde bewaken)

### C5. `d1_sale_combi` — combi-orders multi-magazijn
* Order `d1_combi`, product `d1_default_warehouse_id`; regels krijgen route van het afwijkende magazijn
* **Aandachtspunt:** hardcoded warehouse-ids 1/2 en route-ids 21/22 → instelbaar veld *combi-route* op `stock.warehouse`

### C6. `d1_mrp_sawing` — zagen / lengtes / frames *(grootste cluster)*
* **Product:** `d1_use_qty`, `d1_use_length`, `d1_zaagcap_bew`, `d1_zaagtijd_per_bew`, `d1_artikelcode_gezaagd`, `d1_framecalculator`
* **Orderregel:** `d1_qty`, `d1_length`, `d1_weight` (compute), `d1_frame_id`, `d1_frame_nr` (compute), `d1_qty_var_name`, `d1_use_qty`/`d1_use_length`; onchange `product_uom_qty = qty × length`
* **Productie:** `d1_qty`/`d1_length`/`d1_frame_nr` (van verkoopregel), `d1_productietijd` (zaagformule); werkorderduur automatisch vullen; related velden op werkorder en stock.move; picking-view
* **Controles:** gebruik-lengte vereist gebruik-hoeveelheid; zaagcap/zaagtijd > 0 bij route Productie
* Vervangt ook `d1_fix_studio_fields` (tijdelijke pleister verdwijnt)

### C7. `d1_product_partner_data` — stamdata & views *(sluitstuk)*
* **Product:** `d1_abc_code`, `d1_courant`, `d1_available` (compute — **bevat bug**, zie §3), `d1_package_count` (compute), `d1_cost_calc`
* **Partner/order:** `d1_url_pakbon` (of onderbrengen bij shipping?); resterende form/list-views (partner, product, sale.order) als XPath-extensies
* Defaults (`ir.default`) worden velddefaults in code

**Volgorde:** C1 → C2 → C3 → C4+C6 (C4 hangt op C6-veld; C6 evt. eerst basis-velden) → C5 → C7. Per cluster: kort ontwerp → bouw + tests → migratiescript (data x_studio→d1 + Studio-opschoning) → oplevering.

## 3. Bevindingen die om een besluit vragen

1. **Hardcoded ids** (users 11/13, product 9232 "DeliveryMatch shipping", routes 21/22, warehouses 1/2, picking type "10") → allemaal configureerbaar maken (config-parameters / instelvelden). Vereist eenmalige controle welke records dit op productie zijn.
2. **Bug in `x_studio_available`**: de zoekactie naar de stuklijst gebruikt geen `limit`, en de else-tak zet alleen `False` bij subcontract-stuklijsten — een product zónder voorraad en zónder stuklijst behoudt zijn oude waarde. Nabouwen zoals bedoeld (beschikbaar = voorraad > 0, behalve subcontract) of exact zoals het nu werkt?
3. **Dubbele-referentiecheck** bestaat 2× (onchange + create/write voor API-users) → wordt 1 constraint + 1 onchange; check wordt daarmee ook actief voor gewone gebruikers bij opslaan. Akkoord?
4. **`x_studio_coc`** → migreren naar standaard `company_registry`?
5. **Views op technische modellen** laten vervallen?
6. **"Vul lengte"-automation** (uitgecommentarieerd) definitief laten vervallen?

## 4. Migratie-aanpak (per cluster hetzelfde patroon)

1. Module installeert nieuwe `d1_`-velden.
2. `post_init_hook`/migratiescript kopieert data `x_studio_*` → `d1_*` (SQL, alleen als bronkolom bestaat — draait dus veilig op lege dev-databases én op productie).
3. Zelfde script archiveert/verwijdert de vervangen Studio-onderdelen (automations, views, velden) via de geëxporteerde `xml_id`'s.
4. Smoke-tests per module; oplevering via development → staging (kopie productie = échte migratietest) → productie.

---

## 5. Statusoverzicht oplevering (17 sep 2026)

| Cluster | Module | Bijzonderheden |
|---|---|---|
| C1 | `d1_sale_order_checks` ✅ | Dubbele-referentiecheck geldt nu voor alle gebruikers (besluit) |
| C2 | `d1_sale_dropshipment` ✅ | Hardcoded users [11,13] vervallen (besluit); stored compute dekt UI + API |
| C3 | `d1_purchase_partner_delivery` ✅ | Dropship-uitsluiting = vinkje op operatietype; check vinkje bij deploy als het Dropship-type geen standaardtype is |
| C4 | `d1_sale_extra_service` ✅ | Sommering per dienst-artikel (bugfix t.o.v. Studio) |
| C5 | `d1_sale_combi` ✅ | Combi-route instelbaar per magazijn; Odoo 19 `route_ids` (oude automation schreef verwijderd veld) |
| C6 | `d1_mrp_sawing` ✅ | qty×lengte-logica al aanwezig in `d1_shipping_cost` (afhankelijkheid, wijkt af van besluit "letterlijk" — gemeld); pleister `d1_fix_studio_fields` verwijderd |
| C7 | `d1_product_partner_data` ✅ | Beschikbaar-bug gefixt (besluit); KvK → `company_registry` (besluit); eindschoonmaak: handling-automation/-menu weg, resterende Studio-views gedeactiveerd |

**Deploy-checklist productie:**
1. Vlak vóór de deploy: **export-serveractie nogmaals draaien** op productie en diffen tegen de export van 17-09 — vangt Studio-aanpassingen die ná de inventarisatie zijn gemaakt (les: de test-automation "Voeg volger toe" viel buiten de scope).
2. `development` → staging (kopie productie) mergen: hooks + herstelmigraties draaien daar de échte datamigratie — logs controleren op `could not remove`-meldingen (les van 17/18-09: views met veld-verwijzingen in attributen worden nu gedeactiveerd; automation-matching op ilike).
3. **`d1_studio_compat` installeren (ná stap 2!)** — tijdelijke aliassen voor de oude x_studio-veldnamen, anders breekt de externe koppeling (json2/Conneo) die de oude namen nog gebruikt (les van 18-09: `Invalid field 'x_studio_artikelcode_gezaagd'`). Bewust ná de migraties installeren: een achtergebleven handmatig x_studio-veld botst met de alias.
4. **Integratiepartner (Conneo) de veldmapping oud→nieuw geven** met omschakel-deadline; na omschakeling `d1_studio_compat` deïnstalleren en later uit de repo verwijderen.
5. `d1_fix_studio_fields` deïnstalleren (indien daar geïnstalleerd); map pas uit de repo als de module op álle databases weg is.
6. Dropship-operatietype: vinkje *Geen leverdefaults van leverancier* controleren.
7. Combi-routes op de magazijnen Rotterdam/Wesseling controleren.
8. Gedeactiveerde Studio-views nalopen; gewenste lay-out laten porten, rest verwijderen.
9. Na verificatie: lege modellen `x_handling`/`x_handling_line_b0f2a` handmatig verwijderen.
10. Diagnose-chatternotities leverdatum uitzetten zodra de acceptatie rond is (systeemparameter `d1_sale_commitment_date.explain` → `0`).
11. **API-venster** (alleen indien de koppeling actief is op de doelomgeving): blokkeer tijdens de merge + module-installatie de externe koppeling (Conneo-account tijdelijk archiveren of API-keys intrekken, of connector laten pauzeren) — continue API-writes houden locks vast en laten de build falen (les van 18-09 op staging). *Stand 25-09: Conneo draait nog níet op productie — voor de productie-go-live is geen venster nodig. Zodra Conneo live gaat op productie: omschakeldatum naar de d1_-veldnamen afspreken met de integratiepartner; daarna d1_studio_compat deïnstalleren.*
12. Maatwerk register vullen (na acceptatie, afspraak).

*dooIT B.V. — 17 september 2026*
