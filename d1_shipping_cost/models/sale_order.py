import logging
import math

from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Marker on the transport cost order line so we can identify and replace it.
TRANSPORT_LINE_NAME_MARKER = "[TRANSPORT]"


class SaleOrder(models.Model):
    _inherit = "sale.order"

    d1_transport_message = fields.Text(
        string="Transport berekening",
        readonly=True,
        help="Samenvatting van de laatste transportkostenberekening.",
    )
    d1_pallet_calculation = fields.Boolean(
        string="Palletberekening",
        readonly=True,
        help="Aangevinkt wanneer de transportkosten niet automatisch berekend "
             "konden worden en handmatige palletberekening nodig is.",
    )

    # ------------------------------------------------------------------
    # Public action (button)
    # ------------------------------------------------------------------

    def action_d1_compute_transport_cost(self):
        """Bereken transportkosten voor de huidige offerte/verkooporder.

        Groepeert orderregels per transportklasse (TK1/TK2/TK3), berekent
        per aanwezige klasse de kosten, en voegt één getotaliseerde
        transportkostenregel toe aan de order.
        """
        for order in self:
            order._d1_do_compute_transport()

    # ------------------------------------------------------------------
    # Core calculation orchestrator
    # ------------------------------------------------------------------

    def _d1_do_compute_transport(self):
        """Orchestrator: run TK1/TK2/TK3 calculations and create the order line."""
        self.ensure_one()

        messages = []  # collects user-facing messages per class
        total_cost = 0.0
        has_manual = False  # True if any class requires manual handling

        # Group order lines by shipping class code
        lines_by_class = self._d1_group_lines_by_class()

        # Dispatch map: class code → compute method
        compute_methods = {
            "tk1": self._d1_compute_tk1,
            "tk2": self._d1_compute_tk2,
            "tk3": self._d1_compute_tk3,
        }

        for code in ("tk1", "tk2", "tk3"):
            if lines_by_class.get(code):
                class_name = lines_by_class[code]["class_name"]
                method = compute_methods.get(code)
                if method:
                    cost, msg, manual = method(lines_by_class[code]["lines"])
                    total_cost += cost
                    messages.append(msg)
                    has_manual = has_manual or manual
                else:
                    messages.append(
                        "%s: geen berekeningslogica beschikbaar — overgeslagen." % class_name
                    )
            else:
                messages.append("%s: geen producten in order — overgeslagen." % code.upper())

        # Build summary
        summary = "\n".join(messages)
        if has_manual:
            summary += "\n\n⚠ Er zijn onderdelen die handmatig beoordeeld moeten worden (zie hierboven)."
        summary += "\n\nTotaal transportkosten: € %.2f" % total_cost

        # Write to summary field and pallet flag
        self.d1_transport_message = summary
        self.d1_pallet_calculation = has_manual

        # Post to chatter — wrap in Markup so Odoo renders it as HTML
        self.message_post(
            body=Markup("<strong>Transportkostenberekening</strong><br/><pre>%s</pre>")
            % Markup(summary.replace("\n", "<br/>")),
            subtype_xmlid="mail.mt_note",
        )

        # Create / replace the transport cost order line
        self._d1_set_transport_line(total_cost)

        return True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _d1_group_lines_by_class(self):
        """Return dict {class_code: {class_name, class_id, lines}} for order lines
        that have a shipping class assigned.
        """
        self.ensure_one()
        result = {}
        for line in self.order_line:
            sc = line.product_id.d1_shipping_class_id
            if sc and sc.code:
                code = sc.code.lower().strip()
                if code not in result:
                    result[code] = {
                        "class_name": sc.name,
                        "class_id": sc.id,
                        "lines": self.env["sale.order.line"],
                    }
                result[code]["lines"] |= line
        return result

    def _d1_get_param_float(self, key, default=0.0):
        """Read a float from ir.config_parameter."""
        val = self.env["ir.config_parameter"].sudo().get_param(key, default)
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    def _d1_get_param_int(self, key, default=0):
        """Read an int from ir.config_parameter."""
        val = self.env["ir.config_parameter"].sudo().get_param(key, default)
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return default

    def _d1_get_shipping_partner(self):
        """Return the partner used for address matching (shipping or fallback)."""
        self.ensure_one()
        return self.partner_shipping_id or self.partner_id

    def _d1_find_length_bracket(self, length_cm):
        """Find the d1.shipping.length.bracket that contains the given length.

        Returns a recordset (single record or empty).
        """
        bracket = self.env["d1.shipping.length.bracket"].search([
            ("length_from_cm", "<=", length_cm),
            "|",
            ("length_to_cm", ">=", length_cm),
            ("length_to_cm", "=", 0),  # 0 = open end
        ], limit=1, order="length_from_cm desc")
        return bracket

    def _d1_find_rate(self, shipping_class_id, unit_qty, length_bracket_id=False):
        """Look up the transport rate for the given parameters.

        Searches rates by class, quantity staffel, and length bracket, then
        filters by address match (country/state/zip) against the shipping
        partner. Rates with more specific address restrictions (zip > state >
        country) are preferred by searching all matches and picking the first
        that passes _match_address().

        Args:
            shipping_class_id: int — id of the d1.shipping.class record.
            unit_qty: int — number of units (bundles/boxes).
            length_bracket_id: int or False — id of d1.shipping.length.bracket.

        Returns the price (float) or 0.0 if no matching rate is found.

        # TODO (open punt): Confirm with business whether rates are
        # total-per-bracket or per-unit. Current implementation treats
        # the price field as the total cost for the bracket.
        """
        partner = self._d1_get_shipping_partner()

        domain = [
            ("shipping_class_id", "=", shipping_class_id),
            ("qty_from", "<=", unit_qty),
            "|",
            ("qty_to", ">=", unit_qty),
            ("qty_to", "=", 0),  # 0 = open end
        ]
        if length_bracket_id:
            domain.append(("length_bracket_id", "=", length_bracket_id))
        else:
            domain.append(("length_bracket_id", "=", False))

        # Search all matching rates by staffel, then filter by address.
        # Order: prefer rates with zip_prefix (most specific) first,
        # then rates with country/state, then generic (no address filter).
        rates = self.env["d1.shipping.rate"].search(
            domain, order="qty_from desc"
        )

        # Pick the first rate that matches the delivery address
        for rate in rates:
            if rate._match_address(partner):
                _logger.info(
                    "Order %s: found rate '%s' (€ %.2f) for class=%s, partner=%s, qty=%s",
                    self.name, rate.name, rate.price,
                    rate.shipping_class_id.code,
                    partner.name, unit_qty,
                )
                return rate.price

        _logger.warning(
            "Order %s: no rate found for class_id=%s, partner=%s, qty=%s, bracket_id=%s",
            self.name, shipping_class_id,
            partner.name, unit_qty, length_bracket_id,
        )
        return 0.0

    def _d1_get_class_id(self, code):
        """Return the d1.shipping.class record id for the given code, or False.

        Performs a case-insensitive lookup to be robust against data entry variations.
        """
        sc = self.env["d1.shipping.class"].search([("code", "=ilike", code)], limit=1)
        return sc.id if sc else False

    # ------------------------------------------------------------------
    # TK1 — Bundle calculation (long products / tubes)
    # ------------------------------------------------------------------

    def _d1_compute_tk1(self, lines):
        """Calculate transport cost for TK1 (bundles).

        Flow:
        a) Determine tubes per bundle based on product dimensions vs bundle size.
        b) Determine preliminary number of bundles from total qty.
        c) Correct for max weight per bundle.
        d) Threshold check → pallet (manual) or rate lookup by length bracket.

        Returns: (cost, message_string, is_manual_flag)
        """
        self.ensure_one()
        class_id = self._d1_get_class_id("tk1")

        # Config parameters
        bundle_w = self._d1_get_param_float("d1_shipping.bundle_width_cm", 15.0)
        bundle_h = self._d1_get_param_float("d1_shipping.bundle_height_cm", 15.0)
        bundle_max_kg = self._d1_get_param_float("d1_shipping.bundle_max_weight_kg", 20.0)
        # TODO (open punt): tk1_max_bundels drempelwaarde nog vast te stellen
        tk1_max_bundles = self._d1_get_param_int("d1_shipping.tk1_max_bundels", 99999)

        # --- a) Tubes per bundle ---
        total_bundles = 0
        total_weight = 0.0
        total_qty = 0
        max_length_cm = 0.0
        bundle_details = []

        # Group by product to handle different dimensions
        product_lines = {}
        for line in lines:
            prod = line.product_id
            product_lines.setdefault(prod.id, {"product": prod, "qty": 0})
            product_lines[prod.id]["qty"] += line.product_uom_qty

        for pdata in product_lines.values():
            prod = pdata["product"]
            qty = pdata["qty"]
            total_qty += qty

            w = prod.d1_width_cm or 0.0
            h = prod.d1_height_cm or 0.0
            length = prod.d1_length_cm or 0.0
            weight_per_unit = prod.weight or 0.0  # kg — standard Odoo field

            if length > max_length_cm:
                max_length_cm = length

            total_weight += qty * weight_per_unit

            # Tubes fitting in the bundle cross-section
            tubes_w = max(int(bundle_w // w), 1) if w > 0 else 1
            tubes_h = max(int(bundle_h // h), 1) if h > 0 else 1
            tubes_per_bundle = tubes_w * tubes_h

            # Preliminary bundles for this product
            prod_bundles = math.ceil(qty / tubes_per_bundle) if tubes_per_bundle > 0 else math.ceil(qty)
            total_bundles += prod_bundles

            bundle_details.append(
                "  %s: %d stuks, %d/bundel → %d bundels"
                % (prod.display_name, int(qty), tubes_per_bundle, prod_bundles)
            )

        # --- b) preliminary bundles already summed above ---
        bundles_preliminary = total_bundles

        # --- c) Weight correction ---
        if bundles_preliminary > 0 and total_weight > 0:
            avg_weight_per_bundle = total_weight / bundles_preliminary
            if avg_weight_per_bundle >= bundle_max_kg:
                bundles_corrected = math.ceil(total_weight / bundle_max_kg)
            else:
                bundles_corrected = bundles_preliminary
        else:
            bundles_corrected = bundles_preliminary

        # --- d) Threshold decision ---
        if bundles_corrected >= tk1_max_bundles:
            # TODO (open punt): tk1_max_bundels drempelwaarde nog vast te stellen
            msg = (
                "TK1: %d bundels >= drempel (%d) → PALLETBEREKENING (handmatig).\n%s"
                % (bundles_corrected, tk1_max_bundles, "\n".join(bundle_details))
            )
            _logger.info("Order %s: TK1 pallet threshold reached (%d bundles)", self.name, bundles_corrected)
            return 0.0, msg, True

        # Determine length bracket from configurable d1.shipping.length.bracket
        bracket = self._d1_find_length_bracket(max_length_cm)
        bracket_label = bracket.name if bracket else "onbekend"
        bracket_id = bracket.id if bracket else False

        if not bracket:
            msg = (
                "TK1: %d bundels, max lengte %.0f cm — GEEN LENGTEKLASSE GEVONDEN, "
                "handmatig bepalen.\n%s"
                % (bundles_corrected, max_length_cm, "\n".join(bundle_details))
            )
            return 0.0, msg, True

        price = self._d1_find_rate(class_id, bundles_corrected, length_bracket_id=bracket_id)

        if price == 0.0:
            msg = (
                "TK1: %d bundels, lengteklasse %s — GEEN TARIEF GEVONDEN voor afleveradres, handmatig bepalen.\n%s"
                % (
                    bundles_corrected,
                    bracket_label,
                    "\n".join(bundle_details),
                )
            )
            return 0.0, msg, True

        msg = (
            "TK1: %d bundels (gewichtscorrectie: %s), max lengte %.0f cm (%s), "
            "tarief € %.2f.\n%s"
            % (
                bundles_corrected,
                "ja" if bundles_corrected != bundles_preliminary else "nee",
                max_length_cm,
                bracket_label,
                price,
                "\n".join(bundle_details),
            )
        )
        return price, msg, False

    # ------------------------------------------------------------------
    # TK2 — Box calculation (by weight)
    # ------------------------------------------------------------------

    def _d1_compute_tk2(self, lines):
        """Calculate transport cost for TK2 (boxes by weight, e.g. couplings).

        Flow:
        - Total weight >= threshold → pallet (manual).
        - Otherwise: boxes = ceil(weight / box_max_kg), lookup rate.

        Returns: (cost, message_string, is_manual_flag)
        """
        self.ensure_one()
        class_id = self._d1_get_class_id("tk2")

        # TODO (open punt): tk2_max_gewicht_kg drempelwaarde nog vast te stellen
        tk2_max_kg = self._d1_get_param_float("d1_shipping.tk2_max_gewicht_kg", 99999.0)
        box_max_kg = self._d1_get_param_float("d1_shipping.box_max_weight_kg", 20.0)

        total_weight = sum(l.product_uom_qty * (l.product_id.weight or 0.0) for l in lines)

        if total_weight >= tk2_max_kg:
            msg = (
                "TK2: totaal gewicht %.2f kg >= drempel %.0f kg → PALLETBEREKENING (handmatig)."
                % (total_weight, tk2_max_kg)
            )
            _logger.info("Order %s: TK2 pallet threshold reached (%.2f kg)", self.name, total_weight)
            return 0.0, msg, True

        if box_max_kg <= 0:
            box_max_kg = 20.0
        num_boxes = math.ceil(total_weight / box_max_kg) if total_weight > 0 else 0

        if num_boxes == 0:
            return 0.0, "TK2: geen gewicht → € 0,00.", False

        price = self._d1_find_rate(class_id, num_boxes)

        if price == 0.0:
            msg = (
                "TK2: %d dozen (%.2f kg) — GEEN TARIEF GEVONDEN voor afleveradres, handmatig bepalen."
                % (num_boxes, total_weight)
            )
            return 0.0, msg, True

        msg = "TK2: %.2f kg → %d dozen, tarief € %.2f." % (total_weight, num_boxes, price)
        return price, msg, False

    # ------------------------------------------------------------------
    # TK3 — Display calculation (heavy / voluminous)
    # ------------------------------------------------------------------

    def _d1_compute_tk3(self, lines):
        """Calculate transport cost for TK3 (displays, boards).

        Flow (in strict order):
        1. Total weight >= threshold → pallet (manual).
        2. Per-article checks:
           a. Max weight per article >= 20 kg → pallet (manual).
           b. Max(L, W, H) >= 165 cm → exception Wesseling/Mainfreight.
           c. (L + 2W + 2H) >= 300 cm → exception Wesseling/Mainfreight.
        3. Otherwise: box calculation, same as TK2.

        Returns: (cost, message_string, is_manual_flag)
        """
        self.ensure_one()
        class_id = self._d1_get_class_id("tk3")

        # TODO (open punt): tk3_max_gewicht_kg drempelwaarde nog vast te stellen
        tk3_max_kg = self._d1_get_param_float("d1_shipping.tk3_max_gewicht_kg", 99999.0)
        box_max_kg = self._d1_get_param_float("d1_shipping.box_max_weight_kg", 20.0)

        total_weight = sum(l.product_uom_qty * (l.product_id.weight or 0.0) for l in lines)

        # --- Step 1: total weight threshold ---
        if total_weight >= tk3_max_kg:
            msg = (
                "TK3: totaal gewicht %.2f kg >= drempel %.0f kg → PALLETBEREKENING (handmatig)."
                % (total_weight, tk3_max_kg)
            )
            _logger.info("Order %s: TK3 pallet threshold reached (%.2f kg)", self.name, total_weight)
            return 0.0, msg, True

        # --- Step 2: per-article dimension/weight checks ---
        for line in lines:
            prod = line.product_id
            w_kg = prod.weight or 0.0
            length = prod.d1_length_cm or 0.0
            width = prod.d1_width_cm or 0.0
            height = prod.d1_height_cm or 0.0

            # 2a. Single article weight >= 20 kg → pallet
            if w_kg >= 20.0:
                msg = (
                    "TK3: product '%s' weegt %.2f kg (>= 20 kg) → PALLETBEREKENING (handmatig)."
                    % (prod.display_name, w_kg)
                )
                return 0.0, msg, True

            # 2b. Largest dimension >= 165 cm → exception
            max_dim = max(length, width, height)
            if max_dim >= 165.0:
                # TODO (open punt): TK3 uitzonderingsberekening Wesseling/Mainfreight
                # nog te bepalen. Nu placeholder → handmatige behandeling.
                msg = (
                    "TK3: product '%s' heeft afmeting %.0f cm (>= 165 cm) "
                    "→ UITZONDERING Wesseling/Mainfreight (berekening nog te bepalen)."
                    % (prod.display_name, max_dim)
                )
                return 0.0, msg, True

            # 2c. Girth-like measure: L + 2W + 2H >= 300 cm → exception
            girth = length + 2 * width + 2 * height
            if girth >= 300.0:
                # TODO (open punt): TK3 uitzonderingsberekening Wesseling/Mainfreight
                # nog te bepalen. Nu placeholder → handmatige behandeling.
                msg = (
                    "TK3: product '%s' omtrekmaat %.0f cm (L+2B+2H >= 300 cm) "
                    "→ UITZONDERING Wesseling/Mainfreight (berekening nog te bepalen)."
                    % (prod.display_name, girth)
                )
                return 0.0, msg, True

        # --- Step 3: within limits → box calculation ---
        if box_max_kg <= 0:
            box_max_kg = 20.0
        num_boxes = math.ceil(total_weight / box_max_kg) if total_weight > 0 else 0

        if num_boxes == 0:
            return 0.0, "TK3: geen gewicht → € 0,00.", False

        price = self._d1_find_rate(class_id, num_boxes)

        if price == 0.0:
            msg = (
                "TK3: %d dozen (%.2f kg) — GEEN TARIEF GEVONDEN voor afleveradres, handmatig bepalen."
                % (num_boxes, total_weight)
            )
            return 0.0, msg, True

        msg = "TK3: %.2f kg → %d dozen, tarief € %.2f." % (total_weight, num_boxes, price)
        return price, msg, False

    # ------------------------------------------------------------------
    # Transport cost order line management
    # ------------------------------------------------------------------

    def _d1_set_transport_line(self, total_cost):
        """Remove existing transport line and add a new one with total_cost.

        Uses a dedicated service product (created via data/product_data.xml).
        """
        self.ensure_one()

        transport_product = self.env.ref(
            "d1_shipping_cost.product_transport_cost", raise_if_not_found=False
        )
        if not transport_product:
            raise UserError(
                _("Transportkosten serviceproduct niet gevonden. "
                  "Controleer of de module correct is geïnstalleerd.")
            )

        # Remove existing transport lines
        existing = self.order_line.filtered(
            lambda l: l.product_id == transport_product
        )
        if existing:
            existing.unlink()

        # Add new line (only if cost > 0)
        if total_cost > 0:
            self.env["sale.order.line"].create({
                "order_id": self.id,
                "product_id": transport_product.id,
                "name": "%s Transportkosten" % TRANSPORT_LINE_NAME_MARKER,
                "product_uom_qty": 1,
                "price_unit": total_cost,
                "sequence": 9999,  # place at the end
            })
