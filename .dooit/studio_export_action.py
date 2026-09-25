# =============================================================================
# Studio-export -> definities  (Odoo SERVERACTIE, type "Python-code")
# =============================================================================
# Exporteert ALLE definities van Studio-/handmatige aanpassingen in deze
# database als downloadbaar bestand (Python-literal, machine-leesbaar):
#   - handmatige modellen (ir.model, state=manual)
#   - handmatige velden incl. types, relaties, selecties, compute-code en
#     labels per taal (ir.model.fields, state=manual)
#   - Studio-views + #D1-gemarkeerde views incl. volledige arch
#   - server acties (Studio-getagd + alles gekoppeld aan automations)
#   - alle base.automation records incl. triggers en gekoppelde acties
#   - menu-acties, menu's, standaardwaarden (ir.default), rechten op
#     handmatige modellen
#
# Dit bestand is de bron voor de omzetting van Studio-aanpassingen naar
# d1_-modules (zie dooIT-richtlijnen).
#
# AANMAKEN (eenmalig, op de PRODUCTIE-database):
#   1. Ontwikkelaarsmodus aan.
#   2. Instellingen > Technisch > Serveracties > Nieuw.
#   3. Naam: "d1 Studio-export -> definities".  Model: Contact (res.partner).
#      Type: "Python-code uitvoeren".
#   4. Plak deze code.  Opslaan.
#   5. Klik "Contextuele actie aanmaken".
#   6. Contacten (lijst) > selecteer 1 regel > Actie > "d1 Studio-export".
#   7. Lever het gedownloade bestand aan bij dooIT.
#
# LET OP: safe_eval kent geen import/def; dit script gebruikt die niet.
# -----------------------------------------------------------------------------

langs = [l.code for l in env["res.lang"].search([])]
data = {
    "export_version": 1,
    "database": env.cr.dbname,
    "exported_at": str(datetime.datetime.now()),
    "languages": langs,
}

# ---------------------------------------------------------------- xml-id map
# complete xml-id per (model, res_id) zodat de migratie records kan opruimen
xmlids = {}
for imd in env["ir.model.data"].search([("module", "=", "studio_customization")]):
    xmlids[(imd.model, imd.res_id)] = imd.complete_name

# ---------------------------------------------------------------- modellen
models_out = []
for m in env["ir.model"].search([("state", "=", "manual")]):
    models_out.append({
        "model": m.model,
        "name": m.name,
        "order": m.order or "",
        "transient": bool(m.transient),
        "xml_id": xmlids.get(("ir.model", m.id), ""),
    })
data["models"] = models_out

# ---------------------------------------------------------------- velden
fields_out = []
for f in env["ir.model.fields"].search([("state", "=", "manual")]):
    fields_out.append({
        "model": f.model,
        "name": f.name,
        "ttype": f.ttype,
        "label": f.field_description or "",
        "label_i18n": {
            code: f.with_context(lang=code).field_description or ""
            for code in langs
        },
        "help": f.help or "",
        "relation": f.relation or "",
        "relation_field": f.relation_field or "",
        "relation_table": f.relation_table or "",
        "column1": f.column1 or "",
        "column2": f.column2 or "",
        "required": bool(f.required),
        "readonly": bool(f.readonly),
        "store": bool(f.store),
        "index": bool(f.index),
        "copied": bool(f.copied),
        "translate": bool(f.translate),
        "related": f.related or "",
        "depends": f.depends or "",
        "compute": f.compute or "",
        "domain": f.domain or "",
        "on_delete": f.on_delete or "",
        "size": f.size or 0,
        "tracking": f.tracking or 0,
        "selection": [
            {
                "value": s.value,
                "name": s.name,
                "name_i18n": {
                    code: s.with_context(lang=code).name or ""
                    for code in langs
                },
            }
            for s in f.selection_ids
        ],
        "xml_id": xmlids.get(("ir.model.fields", f.id), ""),
    })
data["fields"] = fields_out

# ---------------------------------------------------------------- views
view_ids = set()
for imd in env["ir.model.data"].search([
    ("module", "=", "studio_customization"), ("model", "=", "ir.ui.view"),
]):
    view_ids.add(imd.res_id)
for v in env["ir.ui.view"].search([("arch_db", "like", "#D1")]):
    view_ids.add(v.id)

views_out = []
for v in env["ir.ui.view"].browse(list(view_ids)).exists():
    inherit_ref = ""
    if v.inherit_id:
        imd2 = env["ir.model.data"].search(
            [("model", "=", "ir.ui.view"), ("res_id", "=", v.inherit_id.id)],
            limit=1,
        )
        inherit_ref = imd2.complete_name if imd2 else "id:%s" % v.inherit_id.id
    views_out.append({
        "name": v.name or "",
        "model": v.model or "",
        "type": v.type or "",
        "key": v.key or "",
        "mode": v.mode or "",
        "priority": v.priority or 0,
        "active": bool(v.active),
        "inherit_ref": inherit_ref,
        "arch": v.with_context(lang="en_US").arch_db or "",
        "arch_i18n": {
            code: v.with_context(lang=code).arch_db or "" for code in langs
        },
        "xml_id": xmlids.get(("ir.ui.view", v.id), ""),
        "is_d1_marked": "#D1" in (v.arch_db or ""),
    })
data["views"] = views_out

# ---------------------------------------------------------------- server acties
sa_ids = set()
for imd in env["ir.model.data"].search([
    ("module", "=", "studio_customization"),
    ("model", "=", "ir.actions.server"),
]):
    sa_ids.add(imd.res_id)
for auto in env["base.automation"].search(["|", ("active", "=", True), ("active", "=", False)]):
    for sa in auto.action_server_ids:
        sa_ids.add(sa.id)
# kinderen van multi-acties meenemen (max. 3 niveaus diep)
for _pass in range(3):
    for sa in env["ir.actions.server"].browse(list(sa_ids)).exists():
        for child in sa.child_ids:
            sa_ids.add(child.id)

actions_out = []
for sa in env["ir.actions.server"].browse(list(sa_ids)).exists():
    actions_out.append({
        "id": sa.id,
        "name": sa.name or "",
        "model": sa.model_id.model if sa.model_id else "",
        "state": sa.state or "",
        "code": sa.code or "",
        "update_field": sa.update_field_id.name if sa.update_field_id else "",
        "update_path": sa.update_path or "",
        "evaluation_type": sa.evaluation_type or "",
        "value": sa.value or "",
        "selection_value": sa.selection_value.name if sa.selection_value else "",
        "resource_ref": str(sa.resource_ref) if sa.resource_ref else "",
        "sequence": sa.sequence or 0,
        "child_ids": [c.id for c in sa.child_ids],
        "usage": sa.usage or "",
        "binding_model": sa.binding_model_id.model if sa.binding_model_id else "",
        "xml_id": xmlids.get(("ir.actions.server", sa.id), ""),
    })
data["server_actions"] = actions_out

# ---------------------------------------------------------------- automations
autos_out = []
for auto in env["base.automation"].search(["|", ("active", "=", True), ("active", "=", False)]):
    autos_out.append({
        "id": auto.id,
        "name": auto.name or "",
        "model": auto.model_id.model if auto.model_id else "",
        "active": bool(auto.active),
        "trigger": auto.trigger or "",
        "trigger_fields": [tf.name for tf in auto.trigger_field_ids],
        "filter_domain": auto.filter_domain or "",
        "filter_pre_domain": auto.filter_pre_domain or "",
        "trg_date_range": auto.trg_date_range or 0,
        "trg_date_range_type": auto.trg_date_range_type or "",
        "action_server_ids": [sa.id for sa in auto.action_server_ids],
        "xml_id": xmlids.get(("base.automation", auto.id), ""),
    })
data["automations"] = autos_out

# ---------------------------------------------------------------- menu-acties
acts_out = []
for imd in env["ir.model.data"].search([
    ("module", "=", "studio_customization"),
    ("model", "=", "ir.actions.act_window"),
]):
    act = env["ir.actions.act_window"].browse(imd.res_id).exists()
    if not act:
        continue
    acts_out.append({
        "name": act.name or "",
        "res_model": act.res_model or "",
        "view_mode": act.view_mode or "",
        "domain": act.domain or "",
        "context": act.context or "",
        "target": act.target or "",
        "xml_id": imd.complete_name,
    })
data["act_windows"] = acts_out

# ---------------------------------------------------------------- menu's
menus_out = []
for imd in env["ir.model.data"].search([
    ("module", "=", "studio_customization"), ("model", "=", "ir.ui.menu"),
]):
    menu = env["ir.ui.menu"].browse(imd.res_id).exists()
    if not menu:
        continue
    menus_out.append({
        "name": menu.name or "",
        "complete_name": menu.complete_name or "",
        "parent": menu.parent_id.complete_name if menu.parent_id else "",
        "action": str(menu.action) if menu.action else "",
        "sequence": menu.sequence or 0,
        "groups": [g.full_name for g in menu.group_ids],
        "xml_id": imd.complete_name,
    })
data["menus"] = menus_out

# ---------------------------------------------------------------- defaults
defaults_out = []
for d in env["ir.default"].search([]):
    f = d.field_id
    if not f or f.state != "manual":
        continue
    defaults_out.append({
        "model": f.model,
        "field": f.name,
        "json_value": d.json_value or "",
        "company": d.company_id.name if d.company_id else "",
        "user": d.user_id.name if d.user_id else "",
        "condition": d.condition or "",
    })
data["defaults"] = defaults_out

# ---------------------------------------------------------------- rechten
access_out = []
for a in env["ir.model.access"].search([("model_id.state", "=", "manual")]):
    access_out.append({
        "name": a.name or "",
        "model": a.model_id.model,
        "group": a.group_id.full_name if a.group_id else "",
        "perm_read": bool(a.perm_read),
        "perm_write": bool(a.perm_write),
        "perm_create": bool(a.perm_create),
        "perm_unlink": bool(a.perm_unlink),
    })
data["access"] = access_out

# ---------------------------------------------------------------- opslaan
payload = repr(data)
attachment = env["ir.attachment"].create({
    "name": "studio_export_%s.pydata" % env.cr.dbname,
    "type": "binary",
    "datas": b64encode(payload.encode("utf-8")),
    "mimetype": "text/plain",
})
action = {
    "type": "ir.actions.act_url",
    "url": "/web/content/%s?download=true" % attachment.id,
    "target": "self",
}
