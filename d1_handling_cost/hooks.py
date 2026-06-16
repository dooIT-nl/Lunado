import logging

from odoo import _

_logger = logging.getLogger(__name__)


def _post_init_migrate_handling(env):
    """Migrate existing Studio x_handling / x_handling_line_b0f2a records
    to the new d1.handling / d1.handling.line models.

    This hook is **idempotent**: it does nothing when d1.handling already
    contains records, so re-installing the module is safe.

    The old Studio models and fields are intentionally left untouched —
    cleanup happens in a separate step after verification.
    """
    # Guard: skip if new model already has data (idempotent)
    if env["d1.handling"].search_count([]) > 0:
        _logger.info(
            "d1_handling_cost: d1.handling already contains records — "
            "skipping migration."
        )
        return

    # Check if the old Studio model exists
    if "x_handling" not in env:
        _logger.info(
            "d1_handling_cost: Studio model x_handling not found — "
            "nothing to migrate."
        )
        return

    old_handlings = env["x_handling"].search([])
    if not old_handlings:
        _logger.info("d1_handling_cost: no x_handling records to migrate.")
        return

    # ------------------------------------------------------------------
    # 1. Migrate d1.handling records (one by one to avoid mail.thread
    #    batch-create issues with the name/tracking field)
    # ------------------------------------------------------------------
    id_map = {}  # {old_handling_id: new_d1_handling_record}
    for old in old_handlings:
        vals = {
            "name": old.x_name or _("(no name)"),
            "active": old.x_active if hasattr(old, "x_active") else True,
            "sequence": getattr(old, "x_studio_sequence", 10) or 10,
        }
        if hasattr(old, "x_studio_currency_id") and old.x_studio_currency_id:
            vals["currency_id"] = old.x_studio_currency_id.id
        if hasattr(old, "x_studio_product") and old.x_studio_product:
            vals["product_id"] = old.x_studio_product.id

        new_rec = env["d1.handling"].create(vals)
        id_map[old.id] = new_rec

    # ------------------------------------------------------------------
    # 2. Migrate d1.handling.line records
    # ------------------------------------------------------------------
    line_count = 0
    if "x_handling_line_b0f2a" in env:
        old_lines = env["x_handling_line_b0f2a"].search([])
        for old_line in old_lines:
            old_handling_id = (
                old_line.x_handling_id.id
                if hasattr(old_line, "x_handling_id") and old_line.x_handling_id
                else False
            )
            new_handling = id_map.get(old_handling_id)
            if not new_handling:
                _logger.warning(
                    "d1_handling_cost: skipping orphan line %s (old handling "
                    "id %s not in mapping).",
                    old_line.id,
                    old_handling_id,
                )
                continue

            env["d1.handling.line"].create({
                "handling_id": new_handling.id,
                "name": getattr(old_line, "x_name", "") or "",
                "sequence": getattr(old_line, "x_studio_sequence", 0) or 0,
                "amount": getattr(old_line, "x_studio_bedrag", 0.0) or 0.0,
                "value_from": getattr(old_line, "x_studio_van", 0.0) or 0.0,
                "total": getattr(old_line, "x_studio_tot", 0.0) or 0.0,
            })
            line_count += 1

    # ------------------------------------------------------------------
    # 3. Migrate res.partner → d1_handling_id
    # ------------------------------------------------------------------
    partner_count = 0
    partners = env["res.partner"].search(
        [("x_studio_handling", "!=", False)]
    )
    for partner in partners:
        old_handling_id = partner.x_studio_handling.id
        new_handling = id_map.get(old_handling_id)
        if new_handling:
            partner.d1_handling_id = new_handling
            partner_count += 1
        else:
            _logger.warning(
                "d1_handling_cost: partner %s references old handling %s "
                "which was not migrated.",
                partner.id,
                old_handling_id,
            )

    _logger.info(
        "d1_handling_cost: migration complete — %d handlings, %d lines, "
        "%d partners migrated.",
        len(id_map),
        line_count,
        partner_count,
    )
