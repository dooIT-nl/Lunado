#!/usr/bin/env python3
"""Generate the d1_shipping_cost user manual in Word (.docx) format."""

from docx import Document
from docx.shared import Pt, Inches, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.style import WD_STYLE_TYPE

doc = Document()

# -- Styles --
style = doc.styles["Normal"]
style.font.name = "Calibri"
style.font.size = Pt(11)
style.paragraph_format.space_after = Pt(6)

for level in range(1, 4):
    hs = doc.styles[f"Heading {level}"]
    hs.font.color.rgb = RGBColor(0x1B, 0x5E, 0x20)  # dark green


def add_table(headers, rows):
    """Add a formatted table to the document."""
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Light Grid Accent 1"
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = h
        for p in cell.paragraphs:
            for r in p.runs:
                r.bold = True
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            table.rows[ri + 1].cells[ci].text = str(val)
    doc.add_paragraph()  # spacing


# ============================================================
# TITLE PAGE
# ============================================================
doc.add_paragraph()
doc.add_paragraph()
title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = title.add_run("Gebruikershandleiding\nTransportkosten (d1_shipping_cost)")
run.font.size = Pt(26)
run.bold = True
run.font.color.rgb = RGBColor(0x1B, 0x5E, 0x20)

subtitle = doc.add_paragraph()
subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = subtitle.add_run("Odoo 19 — dooIT B.V.")
run.font.size = Pt(14)
run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

doc.add_paragraph()
doc.add_paragraph()

info = doc.add_paragraph()
info.alignment = WD_ALIGN_PARAGRAPH.CENTER
info.add_run("Versie 1.0 — Juni 2026").font.size = Pt(11)

doc.add_page_break()

# ============================================================
# TABLE OF CONTENTS (manual)
# ============================================================
doc.add_heading("Inhoudsopgave", level=1)
toc_items = [
    "1. Inleiding",
    "2. Installatie en configuratie",
    "   2.1 Module installeren",
    "   2.2 Transportklassen",
    "   2.3 Lengteklassen",
    "   2.4 Transporttarieven",
    "   2.5 Postcode-prefixen en adresfiltering",
    "   2.6 Instellingen (drempelwaarden)",
    "3. Producten configureren",
    "4. Transportkosten berekenen",
    "   4.1 Berekening starten",
    "   4.2 Resultaat en palletberekening",
    "   4.3 Herberekening",
    "5. Lijstweergave en filteren",
    "",
    "Bijlage A — Berekeningsflows TK1 / TK2 / TK3",
    "Bijlage B — Open punten",
]
for item in toc_items:
    p = doc.add_paragraph(item)
    p.paragraph_format.space_after = Pt(2)

doc.add_page_break()

# ============================================================
# 1. INLEIDING
# ============================================================
doc.add_heading("1. Inleiding", level=1)
doc.add_paragraph(
    "De module Transportkosten (d1_shipping_cost) berekent automatisch de "
    "verzendkosten op offertes en verkooporders in Odoo. De berekening is "
    "gebaseerd op drie transportklassen:"
)
add_table(
    ["Klasse", "Type", "Eenheid", "Voorbeeld"],
    [
        ["TK1", "Bundels (lang)", "Bundels", "Buizen, profielen"],
        ["TK2", "Dozen (gewicht)", "Dozen", "Koppelingen, fittings"],
        ["TK3", "Dozen (display)", "Dozen", "Displays, borden"],
    ],
)
doc.add_paragraph(
    "Per klasse wordt een apart deelproces doorlopen. De som van TK1 + TK2 + TK3 "
    "wordt als één transportkostenregel aan de order toegevoegd. Wanneer de kosten "
    "niet automatisch bepaald kunnen worden (bv. te veel bundels of te zwaar), wordt "
    "de order gemarkeerd voor handmatige palletberekening."
)

# ============================================================
# 2. INSTALLATIE EN CONFIGURATIE
# ============================================================
doc.add_heading("2. Installatie en configuratie", level=1)

doc.add_heading("2.1 Module installeren", level=2)
doc.add_paragraph(
    "De module wordt geïnstalleerd via de Odoo Apps-lijst (zoek op "
    "\"Transportkosten\") of via de command line:"
)
doc.add_paragraph("odoo-bin -i d1_shipping_cost --stop-after-init --no-http", style="No Spacing")
doc.add_paragraph()

doc.add_heading("2.2 Transportklassen", level=2)
doc.add_paragraph("Ga naar: Verkoop → Configuratie → Transport → Transportklassen")
doc.add_paragraph(
    "Hier staan de transportklassen gedefinieerd. Standaard worden TK1, TK2 en TK3 "
    "aangemaakt. Elke klasse heeft een code (hoofdletters, bv. TK1) die intern "
    "gebruikt wordt om de juiste berekeningsflow te selecteren."
)
add_table(
    ["Veld", "Omschrijving"],
    [
        ["Naam", "Weergavenaam, bv. 'TK1 — Bundels'"],
        ["Code", "Technische code (TK1, TK2, TK3). Hoofdletters."],
        ["Omschrijving", "Vrije toelichting"],
        ["Volgorde", "Sorteervolgorde in keuzelijsten"],
    ],
)

doc.add_heading("2.3 Lengteklassen", level=2)
doc.add_paragraph("Ga naar: Verkoop → Configuratie → Transport → Lengteklassen")
doc.add_paragraph(
    "Lengteklassen definiëren bereiken in centimeters voor de TK1-tariefopzoeking. "
    "De maximale productlengte in een order bepaalt welke lengteklasse van toepassing is."
)
add_table(
    ["Veld", "Omschrijving"],
    [
        ["Naam", "Weergavenaam, bv. '< 1,65 m'"],
        ["Lengte vanaf (cm)", "Ondergrens van het bereik (inclusief)"],
        ["Lengte t/m (cm)", "Bovengrens (inclusief). 0 = open einde (geen bovengrens)."],
    ],
)
doc.add_paragraph("Standaard lengteklassen:")
add_table(
    ["Naam", "Van (cm)", "T/m (cm)"],
    [
        ["< 1,65 m", "0", "164"],
        ["1,65 – 2,14 m", "165", "214"],
        [">= 2,15 m", "215", "0 (open)"],
    ],
)
doc.add_paragraph(
    "Tip: Wijzigt de vervoerder de laadruimte-afmetingen? Pas gewoon de cm-waarden "
    "aan of voeg een nieuwe lengteklasse toe. Er is geen codewijziging nodig."
)

doc.add_heading("2.4 Transporttarieven", level=2)
doc.add_paragraph("Ga naar: Verkoop → Configuratie → Transport → Transporttarieven")
doc.add_paragraph(
    "Hier worden de tariefstaffels beheerd. Elk tarief koppelt een transportklasse, "
    "optioneel een lengteklasse, een eenheidsstaffel (van/t.m.) en een adresfilter "
    "aan een prijs."
)
add_table(
    ["Veld", "Omschrijving"],
    [
        ["Naam", "Herkenbare naam voor het tarief"],
        ["Transportklasse", "TK1, TK2 of TK3"],
        ["Lengteklasse", "Alleen voor TK1. Laat leeg voor TK2/TK3."],
        ["Eenheidstype", "Bundels (TK1) of Dozen (TK2/TK3)"],
        ["Aantal vanaf / t.m.", "Staffelbereik. 0 als bovengrens = open einde."],
        ["Tarief", "Prijs voor deze staffel"],
        ["Landen", "Adresfilter: alleen voor deze landen (leeg = alle)"],
        ["Provincies", "Adresfilter: alleen voor deze provincies"],
        ["Postcode-prefixen", "Adresfilter: postcode moet beginnen met prefix"],
    ],
)

doc.add_heading("2.5 Postcode-prefixen en adresfiltering", level=2)
doc.add_paragraph(
    "De adresfiltering werkt identiek aan de standaard Odoo delivery.carrier module. "
    "Per tariefregel kun je optioneel instellen:"
)
doc.add_paragraph("• Landen — tarief geldt alleen voor deze landen", style="List Bullet")
doc.add_paragraph("• Provincies — gefilterd op geselecteerde landen", style="List Bullet")
doc.add_paragraph(
    "• Postcode-prefixen — tarief geldt alleen als de postcode van het afleveradres "
    "begint met een van de opgegeven prefixen",
    style="List Bullet",
)
doc.add_paragraph(
    "Als alle drie leeg zijn, geldt het tarief als generiek (voor alle adressen). "
    "Reguliere expressies worden ondersteund in postcode-prefixen."
)
doc.add_paragraph("Voorbeelden:")
add_table(
    ["Prefix", "Matcht", "Matcht niet"],
    [
        ["8861", "8861AA, 8861 ZZ", "8862AA"],
        ["886", "8861AA, 8862BB, 8869ZZ", "8870AA"],
        ["8861$", "alleen exact '8861'", "8861AA"],
    ],
)

doc.add_heading("2.6 Instellingen (drempelwaarden)", level=2)
doc.add_paragraph("Ga naar: Verkoop → Instellingen → sectie Transportkosten")
doc.add_paragraph("Hier stel je de drempelwaarden en afmetingen in:")
add_table(
    ["Parameter", "Standaard", "Toelichting"],
    [
        ["TK1 max bundels", "99999", "Boven deze waarde → palletberekening"],
        ["Bundelbreedte (cm)", "15", "Breedte van een standaardbundel"],
        ["Bundelhoogte (cm)", "15", "Hoogte van een standaardbundel"],
        ["Max gewicht bundel (kg)", "20", "Max gewicht per bundel"],
        ["TK2 max gewicht (kg)", "99999", "Boven dit totaalgewicht → palletberekening"],
        ["TK3 max gewicht (kg)", "99999", "Boven dit totaalgewicht → palletberekening"],
        ["Max gewicht doos (kg)", "20", "Max gewicht per doos (TK2/TK3)"],
    ],
)

doc.add_page_break()

# ============================================================
# 3. PRODUCTEN CONFIGUREREN
# ============================================================
doc.add_heading("3. Producten configureren", level=1)
doc.add_paragraph("Ga naar een product → tabblad Transport")
doc.add_paragraph("Stel de volgende velden in:")
add_table(
    ["Veld", "Omschrijving"],
    [
        ["Transportklasse", "Kies TK1, TK2 of TK3. Producten zonder klasse worden overgeslagen."],
        ["Lengte (cm)", "Productlengte in centimeters"],
        ["Breedte (cm)", "Productbreedte in centimeters"],
        ["Hoogte (cm)", "Producthoogte in centimeters"],
    ],
)
doc.add_paragraph(
    "Het gewicht wordt gelezen uit het standaard Odoo-veld Gewicht (kg) op het "
    "product. Dit hoeft niet apart ingesteld te worden op het Transport-tabblad."
)

# ============================================================
# 4. TRANSPORTKOSTEN BEREKENEN
# ============================================================
doc.add_heading("4. Transportkosten berekenen", level=1)

doc.add_heading("4.1 Berekening starten", level=2)
doc.add_paragraph(
    "Open een offerte of verkooporder en klik op de knop \"Bereken transportkosten\" "
    "(🚛-icoon) in de header. De module doorloopt per aanwezige transportklasse "
    "de bijbehorende berekeningsflow en voegt één getotaliseerde transportkostenregel "
    "toe aan de order."
)
doc.add_paragraph(
    "Belangrijk: alleen orderregels met een product waarop een transportklasse is "
    "ingesteld worden meegenomen. Regels zonder klasse worden genegeerd."
)

doc.add_heading("4.2 Resultaat en palletberekening", level=2)
doc.add_paragraph("Na de berekening verschijnt onder de orderregels:")
doc.add_paragraph(
    "• Een samenvattingsveld met per klasse het resultaat (aantal bundels/dozen, "
    "tarief, of reden voor handmatige berekening)",
    style="List Bullet",
)
doc.add_paragraph(
    "• Het veld Palletberekening (checkbox) — aangevinkt wanneer de kosten niet "
    "automatisch bepaald konden worden",
    style="List Bullet",
)
doc.add_paragraph(
    "• Een chatterbericht met dezelfde samenvatting (voor audit trail)",
    style="List Bullet",
)
doc.add_paragraph(
    "Wanneer Palletberekening is aangevinkt, wordt er géén transportkostenregel "
    "toegevoegd. De order moet dan handmatig beoordeeld worden."
)

doc.add_heading("4.3 Herberekening", level=2)
doc.add_paragraph(
    "Bij het opnieuw klikken op \"Bereken transportkosten\" wordt de bestaande "
    "transportkostenregel automatisch verwijderd en vervangen door een nieuwe "
    "berekening. Er worden dus nooit dubbele transportkostenregels aangemaakt."
)

# ============================================================
# 5. LIJSTWEERGAVE EN FILTEREN
# ============================================================
doc.add_heading("5. Lijstweergave en filteren", level=1)
doc.add_paragraph(
    "In de lijst van verkooporders is de kolom Palletberekening zichtbaar "
    "(na de klantkolom). Daarnaast is er een zoekfilter \"Palletberekening\" "
    "beschikbaar om snel alle orders te vinden die handmatige beoordeling vereisen."
)

doc.add_page_break()

# ============================================================
# BIJLAGE A — BEREKENINGSFLOWS
# ============================================================
doc.add_heading("Bijlage A — Berekeningsflows TK1 / TK2 / TK3", level=1)

# --- TK1 ---
doc.add_heading("A.1 TK1 — Bundelberekening (lange producten)", level=2)
doc.add_paragraph(
    "Invoer: alle orderregels met transportklasse TK1. Per product zijn breedte, "
    "hoogte, lengte (cm) en gewicht (kg) bekend."
)

doc.add_heading("Stap a) Buizen per bundel", level=3)
doc.add_paragraph(
    "Per product wordt berekend hoeveel stuks in de dwarsdoorsnede van een "
    "standaardbundel passen:"
)
p = doc.add_paragraph()
p.add_run("buizen_in_breedte").bold = True
p.add_run(" = floor(bundelbreedte / artikelbreedte)")
p = doc.add_paragraph()
p.add_run("buizen_in_hoogte").bold = True
p.add_run(" = floor(bundelhoogte / artikelhoogte)")
p = doc.add_paragraph()
p.add_run("buizen_per_bundel").bold = True
p.add_run(" = buizen_in_breedte × buizen_in_hoogte")
doc.add_paragraph(
    "floor = naar beneden afronden. Als de artikelafmeting 0 of groter dan de "
    "bundelmaat is, wordt minimaal 1 aangehouden."
)

doc.add_heading("Stap b) Voorlopig aantal bundels", level=3)
p = doc.add_paragraph()
p.add_run("bundels_voorlopig").bold = True
p.add_run(" = ceil(totaal_aantal_stuks / buizen_per_bundel)")
doc.add_paragraph("ceil = naar boven afronden.")

doc.add_heading("Stap c) Gewichtscorrectie", level=3)
doc.add_paragraph("Controleer of het gemiddelde gewicht per bundel binnen de limiet valt:")
doc.add_paragraph(
    "• Als (totaal_gewicht / bundels_voorlopig) < max_gewicht_bundel → "
    "aantal_bundels = bundels_voorlopig",
    style="List Bullet",
)
doc.add_paragraph(
    "• Anders → aantal_bundels = ceil(totaal_gewicht / max_gewicht_bundel)",
    style="List Bullet",
)

doc.add_heading("Stap d) Drempelbeslissing", level=3)
doc.add_paragraph(
    "• Als aantal_bundels >= TK1 max bundels (instelbaar) → "
    "PALLETBEREKENING (handmatig). Geen automatische prijs.",
    style="List Bullet",
)
doc.add_paragraph(
    "• Anders → bepaal de lengteklasse op basis van de maximale productlengte "
    "in de order (opzoeking in de tabel Lengteklassen) en zoek het tarief op "
    "in de Transporttarieven (klasse TK1 + lengteklasse + staffel + adresfilter).",
    style="List Bullet",
)

doc.add_heading("Rekenvoorbeeld TK1", level=3)
add_table(
    ["Gegeven", "Waarde"],
    [
        ["Product", "Aluminium buis 60×3 mm, lengte 150 cm, gewicht 2 kg"],
        ["Bundelafmeting", "15×15 cm (standaard)"],
        ["Max gewicht bundel", "20 kg"],
        ["Besteld aantal", "50 stuks"],
    ],
)
doc.add_paragraph("Berekening:")
doc.add_paragraph("1. buizen_in_breedte = floor(15 / 3.0) = 5", style="List Number")
doc.add_paragraph("2. buizen_in_hoogte = floor(15 / 3.0) = 5", style="List Number")
doc.add_paragraph("3. buizen_per_bundel = 5 × 5 = 25", style="List Number")
doc.add_paragraph("4. bundels_voorlopig = ceil(50 / 25) = 2", style="List Number")
doc.add_paragraph("5. totaal_gewicht = 50 × 2 = 100 kg", style="List Number")
doc.add_paragraph("6. gemiddeld gewicht/bundel = 100 / 2 = 50 kg > 20 kg → correctie!", style="List Number")
doc.add_paragraph("7. aantal_bundels = ceil(100 / 20) = 5 bundels", style="List Number")
doc.add_paragraph("8. max lengte = 150 cm → lengteklasse '< 1,65 m'", style="List Number")
doc.add_paragraph("9. Tariefopzoeking: TK1, < 1,65 m, 5 bundels → € 25,00", style="List Number")

doc.add_paragraph()

# --- TK2 ---
doc.add_heading("A.2 TK2 — Doosberekening (op gewicht)", level=2)
doc.add_paragraph("Invoer: alle orderregels met transportklasse TK2.")

doc.add_heading("Stap 1) Gewichtsdrempel", level=3)
doc.add_paragraph(
    "• Als totaal_gewicht >= TK2 max gewicht (instelbaar) → PALLETBEREKENING.",
    style="List Bullet",
)

doc.add_heading("Stap 2) Doosberekening", level=3)
p = doc.add_paragraph()
p.add_run("aantal_dozen").bold = True
p.add_run(" = ceil(totaal_gewicht / max_gewicht_doos)")

doc.add_heading("Stap 3) Tariefopzoeking", level=3)
doc.add_paragraph(
    "Zoek in Transporttarieven: klasse TK2, staffel op aantal_dozen, adresfilter."
)

doc.add_heading("Rekenvoorbeeld TK2", level=3)
add_table(
    ["Gegeven", "Waarde"],
    [
        ["Product", "Koppeling, gewicht 0,5 kg"],
        ["Max gewicht doos", "20 kg"],
        ["Besteld aantal", "30 stuks"],
    ],
)
doc.add_paragraph("Berekening:")
doc.add_paragraph("1. totaal_gewicht = 30 × 0,5 = 15 kg (< drempel → door)", style="List Number")
doc.add_paragraph("2. aantal_dozen = ceil(15 / 20) = 1 doos", style="List Number")
doc.add_paragraph("3. Tariefopzoeking: TK2, 1 doos → € 15,00", style="List Number")

doc.add_paragraph()

# --- TK3 ---
doc.add_heading("A.3 TK3 — Displayberekening (volumineus/zwaar)", level=2)
doc.add_paragraph(
    "Invoer: alle orderregels met transportklasse TK3. De beslissingsvolgorde "
    "is strikt:"
)

doc.add_heading("Stap 1) Totaalgewicht-drempel", level=3)
doc.add_paragraph(
    "• Als totaal_gewicht >= TK3 max gewicht → PALLETBEREKENING.",
    style="List Bullet",
)

doc.add_heading("Stap 2) Per-artikel checks", level=3)
doc.add_paragraph("Voor elk product in de TK3-regels wordt gecontroleerd:")
doc.add_paragraph(
    "a) Gewicht per artikel >= 20 kg → PALLETBEREKENING",
    style="List Bullet",
)
doc.add_paragraph(
    "b) Grootste afmeting (L, B of H) >= 165 cm → UITZONDERING Wesseling/Mainfreight "
    "(handmatige behandeling, berekening nog te bepalen)",
    style="List Bullet",
)
doc.add_paragraph(
    "c) Omtrekmaat (L + 2×B + 2×H) >= 300 cm → UITZONDERING Wesseling/Mainfreight",
    style="List Bullet",
)

doc.add_heading("Stap 3) Doosberekening", level=3)
doc.add_paragraph("Als alle checks doorstaan zijn:")
p = doc.add_paragraph()
p.add_run("aantal_dozen").bold = True
p.add_run(" = ceil(totaal_gewicht / max_gewicht_doos)")
doc.add_paragraph("Tariefopzoeking: klasse TK3, staffel op aantal_dozen, adresfilter.")

doc.add_heading("Rekenvoorbeeld TK3", level=3)
add_table(
    ["Gegeven", "Waarde"],
    [
        ["Product", "Display 60×40×30 cm, gewicht 2 kg"],
        ["Besteld aantal", "5 stuks"],
        ["Max gewicht doos", "20 kg"],
    ],
)
doc.add_paragraph("Berekening:")
doc.add_paragraph("1. totaal_gewicht = 5 × 2 = 10 kg (< drempel → door)", style="List Number")
doc.add_paragraph("2. Per artikel: gewicht 2 kg < 20 → OK", style="List Number")
doc.add_paragraph("3. Grootste afmeting = 60 cm < 165 → OK", style="List Number")
doc.add_paragraph("4. Omtrekmaat = 60 + 2×40 + 2×30 = 200 cm < 300 → OK", style="List Number")
doc.add_paragraph("5. aantal_dozen = ceil(10 / 20) = 1 doos", style="List Number")
doc.add_paragraph("6. Tariefopzoeking: TK3, 1 doos → € 20,00", style="List Number")

doc.add_page_break()

# ============================================================
# BIJLAGE B — OPEN PUNTEN
# ============================================================
doc.add_heading("Bijlage B — Open punten", level=1)
doc.add_paragraph(
    "De volgende punten zijn nog niet definitief vastgesteld en moeten met de "
    "business worden afgestemd:"
)
add_table(
    ["#", "Open punt", "Huidige situatie"],
    [
        ["1", "Drempelwaarde TK1 max bundels",
         "Standaard 99999 (= altijd doorrekenen). Vastgesteld worden met business."],
        ["2", "Drempelwaarde TK2/TK3 max gewicht (kg)",
         "Standaard 99999. Vastgesteld worden met business."],
        ["3", "Bundel-/doosafmetingen (15×15 cm, 20 kg)",
         "Zijn aannames. Laten bevestigen door business."],
        ["4", "TK3 uitzondering Wesseling/Mainfreight",
         "Order wordt gevlagd voor handmatige behandeling. "
         "Daadwerkelijke prijsberekening nog te bepalen."],
        ["5", "Tarief-interpretatie",
         "Tarieven worden als totaalbedrag per staffel geïnterpreteerd "
         "(niet per eenheid). Bevestigen met business."],
        ["6", "Carrier-koppeling",
         "Valt buiten scope. Geen verzendkoppeling met externe carriers."],
    ],
)

# ============================================================
# FOOTER
# ============================================================
doc.add_paragraph()
doc.add_paragraph()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("dooIT B.V. — https://dooit.nl")
run.font.size = Pt(9)
run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

# Save
output_path = "/home/odoo/src/user/d1_shipping_cost/static/description/Handleiding_Transportkosten.docx"
doc.save(output_path)
print(f"Handleiding opgeslagen: {output_path}")
