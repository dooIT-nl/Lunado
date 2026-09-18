# d1_studio_compat — TIJDELIJK

Overgangsmodule bij de Studio-conversie: stelt de **oude `x_studio_*`-
veldnamen** beschikbaar als aliassen (related) naar de nieuwe `d1_`-velden,
zodat externe koppelingen (json2 API / Conneo) blijven werken totdat ze zijn
omgezet naar de nieuwe veldnamen.

## Gedekte modellen

`product.template`/`product.product` (12 velden), `res.partner` (8),
`sale.order` (5), `sale.order.line` (8). Lezen én schrijven werkt door naar
de nieuwe velden; berekende velden zijn alleen-lezen (zoals voorheen).

## Bijzonderheden

* **`x_studio_rel_type` / `x_studio_kredietverzekering`**: de oude
  Nederlandse waarden ('Prospect'/'Klant', verzekeringslabels) worden
  vertaald van/naar de nieuwe technische keys — koppelingen hoeven hun
  waarden niet aan te passen. Filteren (domain) op deze twee alias-velden
  wordt niet ondersteund.
* **`x_studio_handling`**: verwijst nu naar `d1.handling`-records; de ids
  wijken af van de oude `x_handling`-ids.
* mrp-/voorraadvelden (productieorder, werkorder, stock.move) hebben geen
  alias — dat waren berekende velden die koppelingen normaliter niet
  bevragen. Nodig? Eenvoudig toe te voegen.

## Installatievolgorde (belangrijk)

Pas installeren **nadat** alle conversie-modules inclusief de
herstelmigraties volledig zijn doorgevoerd: een achtergebleven handmatig
x_studio-veld met dezelfde naam conflicteert met deze aliassen.

## Uitfaseren

1. Integratiepartner zet de koppeling om naar de `d1_`-veldnamen
   (mapping-tabel: zie docs/studio_conversie_plan.md en de handleiding).
2. Module deïnstalleren via Apps.
3. Map uit de repository verwijderen (pas nadat de module op álle databases
   is gedeïnstalleerd).

## Contact

dooIT B.V. — https://dooit.nl
