# Toelichting module `d1_sale_commitment_date`

**Automatische berekening van de leverdatum op verkooporders**

| | |
|---|---|
| Module | `d1_sale_commitment_date` (generiek, dooIT) |
| Odoo-versie | 19.0 (Odoo.sh) |
| Versie | 19.0.1.0.0 |
| Status | Opgeleverd op development-branch, ter acceptatie |
| Afhankelijkheden | `sale_stock`, `mrp` |

Dit document beschrijft de werking van de module en — belangrijker — de **ontwerpkeuzes** die daarin zijn gemaakt. Bij een aantal keuzes zijn bewust aannames gedaan die we graag toetsen; die staan per onderwerp gemarkeerd als **⚠ Discussiepunt** en zijn aan het einde samengevat als beslislijst.

---

## 1. Doel

Bij het opstellen van een offerte wordt de **leverdatum** (`commitment_date`, in Odoo het veld *Delivery Date* op de orderheader) automatisch berekend uit de orderregels, op basis van actuele voorraad, geplande ontvangsten en levertijden van producten. Daarnaast is er een veld voor de **gewenste leverdatum van de klant**, met een waarschuwing als die wens niet haalbaar is.

---

## 2. Functionele werking

### 2.1 Berekening per orderregel

Voor elke orderregel wordt de vroegst mogelijke leverdatum bepaald volgens een watervalmodel:

| Stap | Conditie | Resultaat |
|---|---|---|
| 1 | Voldoende **vrije voorraad** (`free_qty`) in het magazijn van de order | Direct leverbaar → datum = **nu**. De levertijd (`sale_delay`) van het product wordt bewust **genegeerd**. |
| 2 | Onvoldoende voorraad, maar er bestaat een **geplande inkomende ontvangst** (`stock.picking`, type *incoming*, status niet *gereed*/*geannuleerd*) met dit product | Datum = `scheduled_date` van de **eerstvolgende** ontvangst |
| 3 | Onvoldoende voorraad én geen geplande ontvangst | Datum = **nu + `sale_delay`** (levertijd van het product, in dagen) |

Aanvullend:

- De voorraadcheck gebeurt in het **magazijn van de verkooporder** (`warehouse_id`); ontvangsten worden ook gefilterd op dat magazijn en op het bedrijf van de order (multi-company-veilig).
- Hoeveelheden worden altijd omgerekend naar de **basiseenheid** van het product (verkoop in dozen à 12 telt dus correct).
- **Niet-voorraadgehouden producten** (diensten, niet-gevolgde artikelen): voorraad is niet van toepassing, hier geldt altijd *nu + `sale_delay`*.
- Sectie- en notitieregels worden overgeslagen.

### 2.2 Berekening per order

De **laatste** (verste) datum van alle regels wordt de leverdatum van de order. Uitgangspunt is de standaardinstelling *lever alles in één keer* (geen deelleveringen): de order kan pas als álle regels leverbaar zijn.

### 2.3 Kit- en productieartikelen (stuklijsten)

Heeft het product op een orderregel een stuklijst van het type **kit** (*phantom*) of **productie** (*normal*), dan wordt niet het eindproduct maar de **componentenlijst** beoordeeld:

1. De stuklijstregels worden opgehaald (componenten die op basis van productvarianten niet van toepassing zijn, worden overgeslagen — standaard Odoo-gedrag).
2. Benodigd aantal per component = **aantal op de stuklijstregel × aantal op de orderregel**. Conform specificatie wordt hierbij bewust **niet** gedeeld door het aantal op de stuklijst-header (zie discussiepunt K6).
3. Elke component doorloopt daarna **dezelfde waterval** (stap 1–3) als een gewone orderregel.
4. De verste componentdatum bepaalt de datum van de orderregel.

### 2.4 Gewenste leverdatum klant

Nieuw veld op de orderheader: **Customer Requested Date** (`d1_customer_request_date`), naast de bestaande *Delivery Date*.

| Situatie | Gedrag |
|---|---|
| Gewenste datum **later** dan de berekende datum | De gewenste datum wordt overgenomen als leverdatum — er is geen reden eerder te leveren dan de klant wil |
| Gewenste datum **eerder** dan de berekende datum | De **berekende** datum blijft de leverdatum; bovenaan het orderformulier verschijnt een **waarschuwingsbanner** met de eerst haalbare datum |
| Geen gewenste datum ingevuld | De berekende datum is de leverdatum |

De berekende datum blijft altijd zichtbaar in een apart alleen-lezen veld **Computed Delivery Date** (`d1_computed_commitment_date`), zodat verkoop altijd ziet wat systeemtechnisch haalbaar is — ook als de klantwens de leverdatum heeft overschreven.

### 2.5 Wanneer wordt (her)berekend?

- Automatisch bij **aanmaken of wijzigen van orderregels** (product, aantal, eenheid), bij wijziging van het **magazijn** en bij wijziging van de **gewenste klantdatum**.
- Alleen zolang de order in status **Offerte** of **Offerte verzonden** staat.
- Na **bevestiging** wordt de leverdatum **bevroren**: geen herberekening meer, ook niet als regels wijzigen. Odoo neemt de leverdatum bij bevestiging standaard over als geplande datum van de uitleveropdracht.
- Een handmatig ingevulde leverdatum op een openstaande offerte wordt bij de eerstvolgende regelwijziging **overschreven** door de berekening (de gewenste klantdatum is dáárom als apart veld toegevoegd: dat is de plek voor handmatige invoer).

### 2.6 Rekenvoorbeeld

Order met 3 regels, magazijn WH, vandaag = 10 sep:

| Regel | Product | Aantal | Vrije vrd | Eerstvolgende ontvangst | sale_delay | Regeldatum |
|---|---|---|---|---|---|---|
| 1 | Artikel A | 5 | 100 | — | 10 dg | **10 sep** (stap 1: voorraad; delay genegeerd) |
| 2 | Artikel B | 20 | 8 | 25 sep (50 st) | 14 dg | **25 sep** (stap 2: ontvangst) |
| 3 | Artikel C | 3 | 0 | geen | 7 dg | **17 sep** (stap 3: delay) |

→ Leverdatum order = **25 sep** (laatste regeldatum).
Vult de klant *gewenst: 1 okt* in → leverdatum wordt **1 okt**.
Vult de klant *gewenst: 15 sep* in → leverdatum blijft **25 sep** + waarschuwingsbanner.

---

## 3. Ontwerpkeuzes en discussiepunten

Hieronder per keuze: wat er is gebouwd, waarom, welke alternatieven er zijn en wat de consequenties zijn. Dit is de kern van het acceptatiegesprek.

### K1. Voorraadbegrip: vrije voorraad (`free_qty`) ⚠

**Gekozen:** `free_qty` = fysiek aanwezige voorraad **minus reeds gereserveerde** voorraad (reserveringen door bevestigde, nog niet uitgeleverde orders).

**Waarom:** dit is het meest "eerlijke" heden-begrip: wat er nu daadwerkelijk vrij op de plank ligt. Het voorkomt dat een offerte een leverdatum belooft op basis van voorraad die al aan een andere bevestigde order is toegezegd (voor zover gereserveerd).

**Consequenties / alternatieven:**

- `free_qty` kijkt **niet** naar bevestigde orders waarvan de uitlevering **nog niet gereserveerd** is (bijv. bij reservering pas op geplande datum), en niet naar verwachte uitleveringen. In een drukke pijplijn kan de belofte dus optimistisch zijn.
- Alternatief `virtual_available` (voorraad + verwachte ontvangsten − verwachte uitleveringen) is completer, maar zou stap 2 (ontvangsten) deels dubbel meenemen en zegt niets over *wanneer* iets beschikbaar komt.
- Alternatief: `qty_available − uitgaande hoeveelheden` (alle bevestigde vraag aftrekken, ook ongereserveerd) — pessimistischer maar veiliger.
- **Meerdere gelijktijdige offertes** "zien" allemaal dezelfde vrije voorraad; er is geen onderlinge claim. Dat is inherent aan offertes (nog geen verplichting), maar goed om te beseffen.

### K2. Herbevoorrading: eerstvolgende ontvangst, ongeacht hoeveelheid ⚠

**Gekozen:** bij onvoldoende voorraad pakt de module de `scheduled_date` van de **eerstvolgende** geplande inkomende ontvangst waarin het product voorkomt — zonder te controleren of die ontvangst **groot genoeg** is om het tekort te dekken.

**Waarom:** eenvoud en voorspelbaarheid; in verreweg de meeste gevallen dekt de eerstvolgende inkooporder de behoefte.

**Consequenties / alternatieven:**

- Tekort van 100 terwijl morgen 5 stuks binnenkomen → de module belooft morgen. Alternatief is **cumuleren**: ontvangsten optellen tot (vrije voorraad + ontvangen ≥ behoefte) en de datum van de dekkende ontvangst nemen. Dat is nauwkeuriger, maar ook schijnnauwkeurig zolang andere orders diezelfde ontvangsten claimen (er is geen toewijzing van ontvangsten aan orders).
- Reeds geplande **productieorders** (MO's) tellen nu **niet** mee als aanvullingsbron — alleen inkomende pickings. Uitbreidbaar indien gewenst.
- Een ontvangst met `scheduled_date` in het **verleden** (te laat, nog niet verwerkt) wordt gewoon als "eerstvolgende" gezien → de leverdatum kan dan in het verleden uitkomen. Optie: aftoppen op *vandaag*.

### K3. "Direct leverbaar" = vandaag, zonder marge ⚠

**Gekozen:** bij voldoende voorraad is de regeldatum letterlijk *nu* — geen `sale_delay`, geen orderverwerkingstijd, geen *security lead time* uit de voorraadinstellingen, geen rekening met werkdagen/cut-off-tijden.

**Waarom:** conform specificatie ("gebruik geen sale_delay indien voldoende voorraad").

**Alternatief:** een vaste kleine marge (bijv. +1 werkdag verwerkingstijd) of de standaard Odoo *Security Lead Time for Sales* meenemen. Nu belooft een offerte om 16:55 levering "vandaag".

### K4. Beoordeling per regel, niet cumulatief per product ⚠

**Gekozen:** elke regel (en elke stuklijstcomponent) wordt **onafhankelijk** tegen de vrije voorraad gehouden, conform de specificatie "per orderregel".

**Consequentie:** staan er twee regels met hetzelfde product (of twee kits die dezelfde component delen), dan "verbruiken" ze beide dezelfde voorraad. Voorbeeld: vrije voorraad 10, twee regels van elk 8 → beide regels zien "voldoende" terwijl er in totaal 16 nodig zijn.

**Alternatief:** behoefte eerst **aggregeren per product** over de hele order (incl. stuklijstexplosie) en dan pas toetsen. Nauwkeuriger; iets complexer in de beleving ("waarom krijgt regel 2 een latere datum dan regel 1 met hetzelfde product?").

### K5. Productie-artikelen: componentbeschikbaarheid, geen productietijd ⚠

**Gekozen:** bij een stuklijst van het type *productie* kijkt de module wanneer de **componenten** beschikbaar zijn — de verste componentdatum is de regeldatum. De **productiedoorlooptijd** zelf (`produce_delay` op het product, capaciteit van werkplekken) wordt **niet** opgeteld.

**Waarom:** de specificatie vraagt "bom lines ophalen en gebruiken als orderregels"; over productietijd is niets gezegd.

**Consequentie:** de belofte is "componenten binnen = leverbaar", terwijl er feitelijk nog geproduceerd moet worden. **Alternatief:** componentdatum + `produce_delay` dagen. Dit lijkt ons een reëel gewijzigd inzicht — graag bespreken.

### K6. Stuklijstaantal: header-aantal bewust genegeerd ⚠

**Gekozen (letterlijk conform specificatie):** benodigde componenthoeveelheid = *aantal stuklijstregel × aantal orderregel*. Er wordt **niet** gedeeld door het aantal op de stuklijst-header.

**Consequentie:** dit is correct zolang stuklijsten gedefinieerd zijn **per 1 stuk** eindproduct. Is een stuklijst gedefinieerd *per 10 stuks* (header-aantal = 10), dan rekent de module een **factor 10 te veel** componentbehoefte. Standaard Odoo deelt hier wél door. Wij hebben de spec letterlijk gevolgd, maar adviseren te bevestigen dat alle stuklijsten per 1 stuk zijn gedefinieerd — of alsnog te delen door het header-aantal.

### K7. Eén niveau stuklijstexplosie

**Gekozen:** de explosie gaat **één niveau** diep. Een component dat zélf ook een (sub)stuklijst heeft, wordt als gewoon product beoordeeld (voorraad → ontvangst → sale_delay), niet verder geëxplodeerd.

**Alternatief:** recursieve explosie over alle niveaus. Haalbaar, maar de betekenis van "voorraad van een halffabricaat" en productietijden per niveau moeten dan ook worden gedefinieerd. Voorstel: starten met één niveau en uitbreiden als de praktijk erom vraagt.

### K8. Automatische herberekening; handmatige leverdatum wordt overschreven

**Gekozen:** de leverdatum wordt live bijgewerkt zolang de order een offerte is. Handmatig aanpassen van *Delivery Date* op een offerte heeft geen blijvend effect: de eerstvolgende regelwijziging rekent er overheen. De **gewenste klantdatum** is het kanaal voor handmatige sturing (en wint alleen als hij later is).

**Alternatieven:** (a) handmatige invoer laten winnen, (b) berekening alleen via een knop. Gekozen voor volautomatisch omdat een vergeten knop of een achtergebleven handmatige datum tot verkeerde beloftes leidt.

### K9. Bevriezen na bevestiging

**Gekozen:** na orderbevestiging wordt niets meer herberekend. De toegezegde datum is een afspraak met de klant; latere voorraadmutaties horen die afspraak niet stilletjes te wijzigen. Wijzigingen op bevestigde orders zijn een bewust, handmatig proces.

### K10. Datum én tijdstip; verschuivend "nu" ⚠

De leverdatum is in Odoo een **datum + tijdstip**. Stappen 1 en 3 rekenen vanaf *nu*, dus het tijdstip van de berekening. Twee gevolgen:

1. Een offerte die een week blijft liggen, behoudt de oude datum **totdat** iets een herberekening triggert (regelwijziging). De datum "veroudert" dus niet vanzelf mee.
2. Bij `sale_delay` = 7 wordt het exact 7 × 24 uur vanaf het moment van invoer — geen afronding op hele dagen of werkdagen.

**Alternatief:** afronden op einde werkdag / alleen werkdagen tellen. Bewust simpel gehouden tot hier behoefte aan blijkt.

---

## 4. Technische implementatie (voor de liefhebber)

### 4.1 Aangepaste/nieuwe velden op `sale.order`

| Veld | Type | Toelichting |
|---|---|---|
| `commitment_date` | bestaand veld, nu **stored computed, handmatig overschrijfbaar** | Berekening via `_compute_d1_commitment_date`; buiten offerte-status behoudt de compute de bestaande waarde |
| `d1_customer_request_date` | Datetime, nieuw | Gewenste leverdatum klant |
| `d1_computed_commitment_date` | Datetime, stored computed | De puur berekende datum, altijd zichtbaar (alleen-lezen) |
| `d1_delivery_date_warning` | Boolean, computed (niet stored) | Stuurt de waarschuwingsbanner aan: `klantdatum < berekende datum` |

De compute is afhankelijk van `order_line.product_id`, `order_line.product_uom_qty`, `order_line.product_uom_id`, `warehouse_id` en `d1_customer_request_date` — wijzigt één daarvan, dan herberekent Odoo automatisch (ook in de formulierweergave, vóór opslaan).

### 4.2 Kernlogica op `sale.order.line`

- `_d1_get_expected_date()` — regeldatum: uom-conversie → stuklijstexplosie → per component `_d1_get_product_expected_date()` → max.
- `_d1_explode_bom(product, qty)` — zoekt de stuklijst via standaard `mrp.bom._bom_find()` (respecteert bedrijf en varianten); alleen types *phantom*/*normal*; slaat variant-uitgesloten regels over via `_skip_bom_line()`.
- `_d1_get_product_expected_date(product, qty)` — de waterval:
  - `free_qty` opgevraagd met magazijncontext van de order;
  - ontvangst-zoekopdracht: `picking_type_id.code = 'incoming'`, magazijn van de order, `state not in (done, cancel)`, product in de moves, bedrijf van de order, gesorteerd op `scheduled_date`, eerste resultaat;
  - anders `nu + sale_delay`.

Er zijn **geen nieuwe modellen** (daarom geen `ir.model.access.csv`), **geen overrides van standaardmethoden** en **geen wijzigingen aan standaard Odoo-views** — de forms zijn uitgebreid via XPath-inheritance. De module is daarmee upgrade-vriendelijk: verwijderen = terug naar standaardgedrag.

### 4.3 Interactie met standaard Odoo

- Odoo's eigen indicatieve veld *Expected Date* (`expected_date`, gebaseerd op `sale_delay` + security lead time) blijft bestaan en ongewijzigd; onze berekening staat daar los van.
- Bij orderbevestiging gebruikt standaard Odoo de `commitment_date` als geplande datum voor de uitleveropdracht — de berekende belofte stuurt dus automatisch de magazijnplanning aan.

### 4.4 Tests

Zes geautomatiseerde tests (`--test-tags=d1_sale_commitment_date`), alle groen:

1. Voldoende voorraad → vandaag, `sale_delay` genegeerd
2. Geen voorraad, geen ontvangst → nu + `sale_delay`
3. Geen voorraad, wel geplande ontvangst → datum van de ontvangst
4. Meerdere regels → laatste regeldatum wint
5. Kit-stuklijst → componenten bepalen de datum (incl. vermenigvuldiging)
6. Gewenste klantdatum: later wint, eerder geeft waarschuwing en wordt niet overgenomen

---

## 5. Beslislijst voor acceptatie

Samengevat de punten waar we een expliciete keuze van jullie verwachten:

| # | Vraag | Huidige keuze | Alternatief |
|---|---|---|---|
| 1 | Voorraadbegrip (K1) | Vrije voorraad (`free_qty`) | Ook ongereserveerde bevestigde vraag aftrekken / virtueel beschikbaar |
| 2 | Moet de ontvangst het tekort **dekken**? (K2) | Nee — eerstvolgende ontvangst, ongeacht aantal | Cumulatief dekken; evt. MO's meenemen |
| 3 | Ontvangst met datum in het verleden (K2) | Datum wordt ongewijzigd overgenomen | Aftoppen op vandaag |
| 4 | Marge bij "direct leverbaar" (K3) | Geen (letterlijk *nu*) | +X werkdagen verwerkingstijd / security lead time |
| 5 | Voorraad delen tussen regels met hetzelfde product (K4) | Per regel, niet cumulatief | Aggregeren per product over de order |
| 6 | Productietijd optellen bij productie-artikelen (K5) | Nee — alleen componentbeschikbaarheid | + `produce_delay` van het eindproduct |
| 7 | Delen door stuklijst-header-aantal (K6) | Nee (letterlijk conform spec) | Wel delen (standaard Odoo-gedrag) — **bevestig dat alle stuklijsten per 1 stuk zijn gedefinieerd** |
| 8 | Geneste stuklijsten (K7) | Eén niveau | Recursief |
| 9 | Werkdagen / afronding (K10) | Kalenderdagen, exact tijdstip | Afronden op (werk)dagen |

Aanpassing van elk van deze punten is beperkt werk: de logica is bewust in kleine, losse methoden opgezet zodat een gewijzigd inzicht lokaal aangepast kan worden zonder de rest te raken.

---

*dooIT B.V. — september 2026*
