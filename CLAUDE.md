# CLAUDE.md — dooIT Odoo Development Richtlijnen

Deze file beschrijft hoe Claude (en elke andere AI-tool) code, views en
configuratie binnen een dooIT Odoo-project moet genereren. Plak deze file in
de root van elke nieuwe module-repo.

> **Vul aan per project:**
> - Project: `<klant of intern project>`
> - Odoo versie: `19.0`
> - Module prefix: `d1_` (generiek) of `d1_<klantcode>_` (klantspecifiek)

---

## 0. Kernprincipes

* **Taal:** code, identifiers, manifests, log-messages en commit-messages in
**Engels**. Docstrings, README en in-line uitleg mogen Nederlands.
* **Prefix `d1` op alles** wat dooIT toevoegt of overschrijft (models, velden,
XML-id's, groepen, klassen) — zie sectie 1.
* **Views via XPath-extensies** in eigen view-records. Standaard Odoo-XML wordt
in development **nooit** rechtstreeks gewijzigd. (De `#D1`-commentaar-werkwijze
is uitsluitend voor handmatige aanpassingen door consultants, niet voor
gegenereerde code.)
* **Geen klantspecifieke logica in generieke modules.** Maak een klant-module
die `depends` op de generieke module.
* **Bij twijfel: vraag, raad niet.** Liever één extra vraag dan een verkeerde
aanname die later om-gebouwd moet worden.

---

## 1. Naamgeving

### Prefix-tabel

| Wat | Prefix | Voorbeeld |
|-|-|-|
| Eigen module-map | `d1_` | `d1_copy_project_task/` |
| Model `_name` | `d1.` | `_name = "d1.copy.project.task.wizard"` |
| Extra velden op bestaand Odoo-model | `d1_` | `d1_is_template = fields.Boolean(...)` |
| Velden binnen eigen `d1.`-model | geen prefix | `is_template = fields.Boolean(...)` |
| XML view record id | `d1_` | `id="d1_res_partner_view_buttons"` |
| XML view `name`-veld | `.d1` | `name="d1.res.partner.form"` |
| XML action / menu-item id | `d1_` | `id="d1_action_voyage_list"` |
| Cron records (XML id) | `d1_` | `id="d1_cron_clean_logs"` |
| Demo-/data-records (XML id) | `d1_` | `id="d1_demo_partner_acme"` |
| Security group (XML id + label) | `d1_` | `id="d1_group_logistics_manager"` |
| `ir.model.access.csv` id | `access_` | `access_d1_voyage_user` |
| Automated Actions (label) | `d1 ` | `"d1 Factuur versturen bij bevestiging"` |
| Server Actions (label) | `d1 ` | `"d1 Herbereken marge"` |
| Python klassenamen | `D1` | `class D1VoyageLine(models.Model):` |
| Klantspecifieke module | `d1_<klantcode>_` | `d1_acme_invoice_layout` |

### Method-namen (Odoo-conventie)

| Methode-soort | Patroon | Voorbeeld |
|-|-|-|
| Compute | `_compute_<veld>` | `_compute_total_amount` |
| Default | `_default_<veld>` | `_default_user_id` |
| Inverse | `_inverse_<veld>` | `_inverse_partner_name` |
| Search | `_search_<veld>` | `_search_is_overdue` |
| Onchange | `_onchange_<veld>` | `_onchange_partner_id` |
| Constrains | `_check_<beschrijving>` | `_check_quantity_positive` |
| Button-callback | `action_<verb>` | `action_confirm`, `action_send_mail` |
| Cron | `_cron_<beschrijving>` | `_cron_send_reminders` |
| Private helper | `_<naam>` | `_prepare_invoice_vals` |

---

## 2. Views — XPath-extensies (development)

> Voor AI-gegenereerde code: **altijd** XPath-extensies, **nooit** standaard
> Odoo-XML rechtstreeks wijzigen.

```xml
<record id="d1_res_partner_view_form" model="ir.ui.view">
    <field name="name">res.partner.form.d1</field>
    <field name="model">res.partner</field>
    <field name="inherit_id" ref="base.view_partner_form"/>
    <field name="arch" type="xml">
        <xpath expr="//field[@name='vat']" position="after">
            <field name="d1_is_template"/>
        </xpath>
    </field>
</record>
```

**Regels:**

* Record id: `d1_<model>_<view_type>[_<doel>]`
* `<field name="name">`: `<model>.<view_type>.d1[.<doel>]`
* Prefereer `position="after"` / `before` / `attributes` boven `replace`
(minder fragiel bij Odoo-upgrades).
* Gebruik attribuut-matchers (`//field[@name='xxx']`), nooit positie-selectors
zoals `//div[1]/div[3]`.
* Eén view-record per logische aanpassing — niet meerdere onsamenhangende
wijzigingen samen.

---

## 3. Module-structuur

```
d1_mijn_module/
├── __init__.py                       # alleen imports, geen logica
├── __manifest__.py
├── README.md
├── models/
│   ├── __init__.py
│   └── <model>.py
├── views/
│   └── <model>_views.xml
├── wizards/
├── reports/
├── data/
├── demo/
├── security/
│   ├── ir.model.access.csv
│   └── <module>_security.xml         # groepen + record rules
├── controllers/                      # alleen indien nodig
├── i18n/                             # .pot + .po
├── static/
│   └── description/
│       ├── icon.png                  # dooIT logo (verplicht)
│       └── index.html                # optioneel
└── tests/
    ├── __init__.py
    └── test_<feature>.py
```

---

## 4. Manifest

* **Taal:** Engels.
* **Verplicht:** `name, summary, version, category, author, license, depends, data, installable`.
* **Vast:** `"author": "dooIT B.V."`, `"license": "LGPL-3"`.
* **`depends`:** zo minimaal mogelijk — alleen wat echt nodig is.
* **`application`:** `False`, tenzij het een volwaardige standalone app is.
* **`version`:** `<odoo-versie>.<major>.<minor>.<patch>` (bv. `19.0.1.5.0`).
* **`description`:** changelog — zie hieronder.

```python
{
    "name": "Copy Project Tasks from Template",
    "summary": "Copy tasks (including subtasks) from template projects",
    "version": "19.0.1.5.0",
    "category": "Project",
    "author": "dooIT B.V.",
    "website": "https://dooit.nl",
    "license": "LGPL-3",
    "depends": ["project"],
    "data": [
        "security/ir.model.access.csv",
        "security/d1_copy_project_task_security.xml",
        "wizards/copy_project_task_wizard_views.xml",
        "views/project_project_views.xml",
    ],
    "installable": True,
    "application": False,
    "description": """
        Copy Project Tasks 19.0.1.5.0
        =============================
        * v1.5: ondersteuning voor subtaak-deadlines
        * v1.4: optie om assignees mee te kopiëren
    """,
}
```

---

## 5. Python / Modellen

### Bestandsindeling (top of file)

```python
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)
```

### Volgorde binnen een model-klasse

1. `_name`, `_description`, `_inherit`, `_order`, `_rec_name`, `_sql_constraints`
2. Velden (logisch gegroepeerd of alfabetisch)
3. `_default_*` methoden
4. `@api.depends` compute-methoden
5. `@api.onchange`
6. `@api.constrains`
7. CRUD-overrides (`create`, `write`, `unlink`, `copy`)
8. `action_*` business-methoden
9. Private helpers

### Regels

* **Geen bare `except:`.** Minimaal `except Exception as e:` met
`_logger.exception(...)` of `_logger.error(...)`.
* **Docstring per publieke methode** — wat doet het, welke context wordt
verwacht, wat is de return.
* **Geen logica in `__init__.py` of `__manifest__.py`** (`__init__.py` doet
alleen imports).
* **Validaties:** `_sql_constraints` voor database-niveau, aanvullend
`@api.constrains` voor business-logica.
* **`_()` rond alle user-facing strings** (UserError, notificaties, labels).
* **Excepties:** `UserError` voor verwachte fouten, `ValidationError` voor
constraint-violations, `AccessError` voor permissies.
* **Vermijd `.sudo()`** — alleen gebruiken als security-bypass bewust nodig
is, met commentaar waarom.
* **Vermijd `self.env.cr.execute()`** — alleen als ORM ontoereikend is. Altijd
parameterized queries, nooit string-interpolatie.
* **Recordset-vriendelijk:** methoden werken op `self` als recordset, niet als
enkele record. Gebruik `for rec in self:` waar nodig.
* **Gebruik `mapped()`, `filtered()`, `sorted()`** boven Python-loops.
* **Datums:** `fields.Datetime` (UTC); conversie naar user-tz doet Odoo.
* **Bedragen:** `fields.Monetary(currency_field='currency_id')` — nooit
`fields.Float` voor geld.

---

## 6. Security

### `security/ir.model.access.csv`

* Altijd aanmaken, ook bij tijdelijk open access — documenteer dan expliciet
waarom.
* Eén regel per (model × groep).
* Id-naamgeving: `access_<model_snake>_<group_short>`.
* Alle vier perms expliciet (`perm_read,perm_write,perm_create,perm_unlink`).

### `security/<module>_security.xml` (groepen + record rules)

* Groep-id's: `d1_group_<module>_user`, `d1_group_<module>_manager`.
* Manager erft van user via `implied_ids`.
* Categorie via `category_id` (eigen of `base.module_category_*`).
* **Record rules voor row-level security** — niet via Python-filtering in
methoden.
* **Multi-company:** rules altijd met
`('company_id', 'in', company_ids)` of `('company_id', '=', False)`.

---

## 7. Studio vs Maatwerk

| Situatie | Aanpak |
|-|-|
| Eenvoudig extra veld, geen logica | Studio |
| Aanpassing lay-out bestaande view (handmatig) | Studio of `#D1`-werkwijze |
| Compute-veld, constraint, Python-logica | Maatwerk module |
| Integratie met extern systeem | Altijd maatwerk module |

Studio-wijzigingen zijn niet versioned. Documenteer in `README.md` van de
module (of in een notitieveld in Odoo) welke aanpassingen via Studio zijn
gedaan. Exporteer periodiek als module.

---

## 8. Automated Actions & Server Actions

* Naam-label begint met `d1 ` (spatie, geen underscore).
* `description`-veld vult **doel, aanmaakdatum, auteur**.
* Test eerst handmatig als Server Action vóór je de trigger activeert.

---

## 9. Logging

* `_logger.info(...)` — business-events.
* `_logger.warning(...)` — onverwachte maar herstelbare situaties.
* `_logger.error(...)` / `_logger.exception(...)` — echte fouten.
* **Geen `print()`** in productiecode.
* **Geen gevoelige data** in logs (klantgegevens, tokens, wachtwoorden, PII).

---

## 10. Vertalingen (i18n)

* Wrap user-facing strings in `_()` (geïmporteerd uit `odoo`).
* Exporteer `.pot` per module:
`odoo-bin --i18n-export=i18n/d1_mijn_module.pot -d <db> --modules=d1_mijn_module`.
* Plaats taal-bestanden in `i18n/`: `nl_NL.po`, `en_US.po`.

---

## 11. Performance

* **Aggregaties:** `read_group()` in plaats van Python-sum loops.
* **Vermijd N+1:** `partners.mapped('country_id.name')` i.p.v. loop met
attribute-access.
* **Indexes:** `fields.Char(index=True)` op velden gebruikt in
search/domain/group_by.
* **Stored compute:** alleen als je erop zoekt of het in een
tree/kanban-view toont. Anders non-stored.
* **`@api.depends(...)`:** vermeld alle dependencies expliciet — anders
herberekent Odoo niet.
* **Batches:** vermijd `for record in big_recordset: record.write({...})` —
doe `big_recordset.write({...})` of split per groep.

---

## 12. Testen

* `tests/__init__.py` importeert alle test-bestanden.
* Tests erven van `odoo.tests.common.TransactionCase` (of `HttpCase` voor
controllers).
* **Minimaal één smoke-test per kritisch model:** create, default values, key
compute, één business-action.
* Tag tests met `@tagged('d1_<module>')` zodat ze selectief draaibaar zijn:
`--test-tags=d1_<module>`.

---

## 13. Git & Odoo.sh

* **Repo:** `https://github.com/dooIT-nl/modules` — module op juiste
versie/branch.
* **Branching:** nooit direct op `main`. Branch per feature of
klant-aanpassing.
* **Branch-naam:** `feature/d1_<module>` of `fix/d1_<module>_<short>`.
* **Conventional commits:**

  * `feat: d1_voyage — voeg lading-tracking toe aan voyage lines`
  * `fix: d1_powerpick — bare except vervangen door exception logging`
  * `docs: d1_voyage — manifest changelog bijgewerkt naar v14.13.5`
* **PR review verplicht** voor productie-merges.
* **`.gitignore` minimaal:** `*.pyc`, `__pycache__/`, `.idea/`, `.vscode/`,
`*.swp`, `.DS_Store`, `.env`.
* **Geen credentials/API-keys/klantdata in code.**

  * Configureerbare waarden → `ir.config_parameter`.
  * Secrets → Odoo.sh environment variables.

---

## 14. Documentatie per module

Elke module bevat minimaal:

* `README.md` — doel, installatie-instructies, gebruikersinstructies, bekende
beperkingen, contactpersoon.
* `__manifest__.py` `description` — changelog (zie sectie 4).
* `static/description/icon.png` — dooIT logo (verplicht voor herkenbaarheid in
de Apps-lijst).
* `static/description/index.html` — optioneel, voor uitgebreidere weergave in
Apps-overzicht.

---

## 15. Klantspecifieke modules

* **Geen** klantspecifieke logica in generieke modules.
* Klant-module `depends` op (of erft van) de generieke module.
* Naam: `d1_<klantcode>_<functie>` — bv. `d1_acme_invoice_layout`.

---

## 16. Werkwijze voor Claude

Wanneer je een module of feature genereert:

1. **Vraag eerst** wat onduidelijk is — Odoo-versie, klantcode, exacte scope.
2. **Lever een complete module-structuur** (alle `__init__.py`'s, manifest,
security CSV, minimaal één test) — geen halve oplevering.
3. **Volg de prefix- en method-naamgeving exact** (sectie 1).
4. **Views: altijd XPath-extensies** (sectie 2). Geen directe wijziging van
standaard Odoo-XML.
5. **`_()`** rond alle user-facing strings.
6. **Smoke-test** in `tests/` bij elk nieuw model.
7. **Manifest `description`** bijwerken met versie-bullet bij elke wijziging.
8. **Verklaar afwijkingen** — als een richtlijn niet past in een specifiek
geval, geef expliciet aan waarom je afwijkt en wacht op bevestiging.
