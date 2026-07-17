# Transportkosten (d1_shipping_cost)

Odoo 19 module voor het berekenen van transportkosten op basis van drie
transportklassen (TK1, TK2, TK3) op offertes en verkooporders.

## OPEN PUNTEN / TODO

1. **Drempelwaarden** `tk1_max_bundels` (max aantal bundels vóór pallet) en
   `tk2_max_gewicht_kg` / `tk3_max_gewicht_kg` (max gewicht vóór pallet)
   zijn nog **niet vastgesteld**. Huidige defaults zijn zeer hoog (99999)
   zodat de berekening altijd doorloopt — stel deze bij via
   Verkoop > Instellingen > Transportkosten.

2. **Bundel-/doosafmetingen** (15×15 cm bundel, 20 kg max per bundel/doos)
   zijn **aannames** — laten bevestigen door business.

3. **TK3 uitzonderingsberekening** (Wesseling / Mainfreight): wanneer een
   TK3-product een afmeting ≥ 165 cm heeft of een omtrekmaat (L+2B+2H) ≥ 300 cm,
   wordt de order gevlagd voor handmatige behandeling. De daadwerkelijke
   prijsberekening voor deze uitzondering is **nog te bepalen**.

4. **Carrier-koppeling** (daadwerkelijk versturen via carrier API) valt
   **buiten scope** van deze module.

5. **Tarief-interpretatie**: tarieven worden nu als totaalbedrag per staffel
   geïnterpreteerd (niet per eenheid). Bevestig met business of dit correct is.

## Installatie

```bash
odoo-bin -i d1_shipping_cost --stop-after-init --no-http
```

## Gebruik

1. **Producten configureren**: ga naar een product > tabblad "Transport" en
   stel de transportklasse (TK1/TK2/TK3) en afmetingen in. Gewicht wordt
   uit het standaard gewichtsveld gelezen.
   - **Gebruik Hoeveelheid**: vink aan om de orderregel-hoeveelheid te berekenen
     als `d1_qty × d1_length_cm` (i.p.v. handmatige invoer).
   - **Gebruik Lengte**: vink aan om een afwijkende lengte per orderregel toe te
     staan. Als dit uit staat, wordt de productlengte automatisch ingevuld.

2. **Tarieven beheren**: Verkoop > Configuratie > Transporttarieven.
   Vul de staffels per klasse, land en eenheidsbereik in.

3. **Parameters instellen**: Verkoop > Instellingen > sectie
   "Transportkosten" voor drempelwaarden en bundel-/doosafmetingen.

4. **Berekenen**: open een offerte/verkooporder en klik op
   "Bereken transportkosten". De module berekent per klasse de kosten en
   voegt één transportkostenregel toe. Het resultaat wordt ook in de
   chatter gepost.

## Transportklassen

| Klasse | Type              | Eenheid | Voorbeeld            |
|--------|-------------------|---------|----------------------|
| TK1    | Bundels (lang)    | Bundels | Buizen, profielen    |
| TK2    | Dozen (gewicht)   | Dozen   | Koppelingen, fittings|
| TK3    | Dozen (display)   | Dozen   | Displays, borden     |

## Berekeningsflows

### TK1 — Bundels (met gewichtsbanding)
1. **Gewichtsbanding per stuk** (vóór bundelberekening):
   - Stukgewicht ≥ max bundel-kg → hele TK1 = palletberekening (handmatig).
   - max/2 ≤ stukgewicht < max → één-per-bundel pool (bundels = aantal stuks).
   - Stukgewicht < max/2 → normale geometrische berekening pool.
2. Normale pool: bepaal buizen per bundel o.b.v. productafmetingen vs bundelgrootte,
   gewichtscorrectie.
3. **Totaal bundels = één-per-bundel + normaal**.
4. Drempelcheck → pallet (handmatig) of tariefopzoeking per lengteklasse.

### TK2 — Dozen op gewicht (met gewichtsbanding)
1. Totaalgewicht-check → pallet indien boven instelbare drempel.
2. **Gewichtsbanding per stuk** (vóór doosberekening):
   - Stukgewicht ≥ max doos-kg → hele TK2 = palletberekening (handmatig).
   - max/2 ≤ stukgewicht < max → één-per-doos pool (dozen = aantal stuks).
   - Stukgewicht < max/2 → normale gewichtssommering pool.
3. Normale pool: dozen = ceil(totaalgewicht / max kg per doos).
4. **Totaal dozen = één-per-doos + normaal**.
5. Tariefopzoeking.

### TK3 — Displays
1. Totaalgewicht-check → pallet indien boven drempel.
2. Per product: gewicht-, afmeting- en omtrekcheck.
3. Binnen grenzen → doosberekening zoals TK2.

## Auteur

dooIT B.V. — https://dooit.nl
