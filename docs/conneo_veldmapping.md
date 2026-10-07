# Veldmapping Conneo: x_studio → d1 (Lunado, Odoo 19)

| | |
|---|---|
| Doel | Omschakeling van de Conneo-koppeling (json2 RPC) van oude Studio-veldnamen naar de nieuwe d1_-velden |
| Aanleiding | Studio-maatwerk is vervangen door beheerde d1_-modules; op productie bestaan de x_studio-velden niet meer |
| Overgang | Op de test-staging is `d1_studio_compat` geïnstalleerd: daar werken de oude namen tijdelijk als alias. **Productie krijgt deze compat-laag niet** — de koppeling wordt pas op productie toegelaten als ze volledig op d1_-namen draait |
| Bron | `d1_studio_compat` v19.0.1.0.1 (elke alias hieronder = een veld dat de koppeling vandaag gebruikt) |
| Contact | dooIT B.V. — bertjan@dooit.nl |

## product.template (ook bereikbaar via product.product)

| Oud veld (Studio) | Nieuw veld (d1) | Type | Schrijfbaar | Bijzonderheden |
|---|---|---|---|---|
| `x_studio_use_qty` | `d1_use_qty` | Boolean | ja | |
| `x_studio_use_length` | `d1_use_length` | Boolean | ja | |
| `x_studio_zaagcap_bew` | `d1_saw_capacity` | Integer | ja | |
| `x_studio_zaagtijd_per_bew` | `d1_saw_time` | Integer | ja | |
| `x_studio_artikelcode_gezaagd` | `d1_raw_product_id` | Many2one → product.template | ja | Betekenis omgedraaid vastgelegd: verwijst naar het hele-lengte-artikel (label "Artikelcode hele lengte") |
| `x_studio_framecalculator_janee` | `d1_framecalculator` | Boolean | ja | |
| `x_studio_abc_code` | `d1_abc_code` | Selection | ja | Waarden: `04`, `05`, `06`, `07` (ongewijzigd) |
| `x_studio_courant` | `d1_courant` | Boolean | ja | |
| `x_studio_available` | `d1_available` | Boolean | **nee** | Berekend (voorraad > 0, behalve subcontract-stuklijst) |
| `x_studio_aantal_verpakkingen` | `d1_package_count` | Integer | **nee** | Berekend (aantal verpakkings-UoM's) |
| `x_studio_kostprijs_calc` | `d1_cost_calc` | Monetary | ja | |
| `x_studio_default_warehouse_id` | `d1_default_warehouse_id` | Many2one → stock.warehouse | ja | |

## res.partner

| Oud veld (Studio) | Nieuw veld (d1) | Type | Schrijfbaar | Bijzonderheden |
|---|---|---|---|---|
| `x_studio_dropshipment` | `d1_dropshipment` | Boolean | ja | |
| `x_studio_verzekerd_bedrag` | `d1_insured_amount` | Float | ja | |
| `x_studio_incoterm_id` | `d1_incoterm_id` | Many2one → account.incoterms | ja | |
| `x_studio_type_levering` | `d1_delivery_picking_type_id` | Many2one → stock.picking.type | ja | |
| `x_studio_handling` | `d1_handling_id` | Many2one → d1.handling | ja | **Let op:** nieuwe record-ids — de oude x_handling-ids zijn niet geldig; records zijn gemigreerd naar het model `d1.handling` |
| `x_studio_coc` | `company_registry` | Char | ja | Standaard Odoo-veld (KvK-nummer) |
| `x_studio_rel_type` | `d1_rel_type` | Selection | ja | **Waarden gewijzigd:** `Prospect` → `prospect`, `Klant` → `customer` |
| `x_studio_kredietverzekering` | `d1_credit_insurance` | Selection | ja | **Waarden gewijzigd:** `Verzekerd, eigen beoordeling` → `insured_own`; `Verzekerd, beoordeling verzekeraar` → `insured_insurer`; `Niet verzekerd` → `not_insured` |

## sale.order

| Oud veld (Studio) | Nieuw veld (d1) | Type | Schrijfbaar | Bijzonderheden |
|---|---|---|---|---|
| `x_studio_dropshipment` | `d1_dropshipment` | Boolean | ja | Wordt bij aanmaken automatisch voorgevuld vanaf de klant |
| `x_studio_combi` | `d1_combi` | Boolean | ja | |
| `x_studio_exceed_credit_limit` | `d1_exceed_credit_limit` | Boolean | ja | |
| `x_studio_credit_limit_exceeded` | `d1_credit_limit_exceeded` | Boolean | **nee** | Berekend |
| `x_studio_url_pakbon` | `d1_delivery_note_url` | Char | ja | |

## sale.order.line

| Oud veld (Studio) | Nieuw veld (d1) | Type | Schrijfbaar | Bijzonderheden |
|---|---|---|---|---|
| `x_studio_qty` | `d1_qty` | Float | ja | Bij zaagartikelen: besteld aantal = d1_qty × d1_length (automatisch) |
| `x_studio_length` | `d1_length` | Float | ja | |
| `x_studio_use_qty` | `d1_use_qty` | Boolean | **nee** | Volgt het product |
| `x_studio_use_length` | `d1_use_length` | Boolean | **nee** | Volgt het product |
| `x_studio_weight` | `d1_weight` | Float | **nee** | Berekend |
| `x_studio_frame_id` | `d1_frame_id` | Char | ja | |
| `x_studio_frame_nr` | `d1_frame_nr` | Char | **nee** | Berekend |
| `x_studio_qty_var_name` | `d1_qty_var_name` | Char | ja | |

## Afspraken

1. **Testen:** de omgeschakelde koppeling eerst tegen de test-staging draaien. Daar zijn beide veldensets actief (compat), dus de omschakeling kan veld voor veld worden gevalideerd.
2. **Niet-schrijfbare velden** (kolom "Schrijfbaar" = nee) niet meer meesturen in create/write-calls — dit zijn berekende velden; meesturen gaf in Studio ook al geen betrouwbaar effect.
3. **Gebruikt de koppeling een x_studio-veld dat hier níet in staat?** Meld het bij dooIT — dat veld is bewust vervallen of over het hoofd gezien.
4. **Deadline:** in overleg; de koppeling wordt op productie geactiveerd zodra deze omschakeling gereed en getest is. Daarna wordt de compat-laag overal verwijderd.

*dooIT B.V. — 25 september 2026*
