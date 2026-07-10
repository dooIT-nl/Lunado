import logging
import math

from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Marker on the transport cost order line so we can identify and replace it.
TRANSPORT_LINE_NAME_MARKER = "[TRANSPORT]"

# Carrier priority: TK1 takes precedence over TK3, TK3 over TK2.
_CARRIER_PRIORITY = ("tk1", "tk3", "tk2")


class SaleOrder(models.Model):
    _inherit = "sale.order"

    d1_transport_message = fields.Text(
        string="Transport Calculation",
        readonly=True,
        help="Summary of the last transport cost calculation.",
    )
    d1_pallet_calculation = fields.Boolean(
        string="Pallet Calculation",
        readonly=True,
        help="Checked when transport costs could not be calculated automatically "
             "and manual pallet calculation is needed.",
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
        """Orchestrator: run TK1/TK2/TK3 calculations, determine carrier, create order line."""
        self.ensure_one()

        messages = []  # collects user-facing messages per class
        total_cost = 0.0
        has_manual = False  # True if any class requires manual handling
        carriers = {}  # {class_code: carrier_id or False}

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
                    cost, msg, manual, carrier_id = method(lines_by_class[code]["lines"])
                    total_cost += cost
                    messages.append(msg)
                    has_manual = has_manual or manual
                    carriers[code] = carrier_id
                else:
                    messages.append(
                        "%s: geen berekeningslogica beschikbaar — overgeslagen." % class_name
                    )
            else:
                messages.append("%s: geen producten in order — overgeslagen." % code.upper())

        # Determine carrier based on priority: TK1 > TK3 > TK2
        selected_carrier_id = False
        carrier_source = ""
        for code in _CARRIER_PRIORITY:
            if carriers.get(code):
                selected_carrier_id = carriers[code]
                carrier_source = code.upper()
                break

        # Build summary
        summary = "\n".join(messages)
        if selected_carrier_id:
            carrier_name = self.env["delivery.carrier"].browse(selected_carrier_id).display_name
            summary += "\n\nTransporteur: %s (bepaald door %s)" % (carrier_name, carrier_source)
        elif any(lines_by_class.get(c) for c in ("tk1", "tk3", "tk2")):
            summary += "\n\nTransporteur: handmatig selecteren"
        if has_manual:
            summary += "\n\n⚠ Er zijn onderdelen die handmatig beoordeeld moeten worden (zie hierboven)."
        summary += "\n\nTotaal transportkosten: € %.2f" % total_cost

        # Write to summary field, pallet flag and carrier
        self.d1_transport_message = summary
        self.d1_pallet_calculation = has_manual
        self.carrier_id = selected_carrier_id

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

        Returns a tuple (price, carrier_id):
            - price: float — the rate price, or 0.0 if not found.
            - carrier_id: int or False — the preferred carrier from the rate.
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
                    "Order %s: found rate '%s' (€ %.2f, carrier=%s) for class=%s, partner=%s, qty=%s",
                    self.name, rate.name, rate.price,
                    rate.carrier_id.display_name or "-",
                    rate.shipping_class_id.code,
                    partner.name, unit_qty,
                )
                return rate.price, rate.carrier_id.id or False

        _logger.warning(
            "Order %s: no rate found for class_id=%s, partner=%s, qty=%s, bracket_id=%s",
            self.name, shipping_class_id,
            partner.name, unit_qty, length_bracket_id,
        )
        return 0.0, False

    def _d1_get_class_id(self, code):
        """Return the d1.shipping.class record id for the given code, or False.

        Performs a case-insensitive lookup to be robust against data entry variations.
        """
        sc = self.env["d1.shipping.class"].search([("code", "=ilike", code)], limit=1)
        return sc.id if sc else False

    # ------------------------------------------------------------------
    # Shared helper: piece weight & qty for length-based products
    # ------------------------------------------------------------------

    def _d1_piece_weight(self, product, line, meter_uom):
        """Return the weight of a single piece for an order line.

        ``product.weight`` is per unit of measure.  When the product is
        sold by a length UoM (m, cm, mm …) the weight must be multiplied
        by the piece length to obtain the actual piece weight.

        :param product:   product.product record
        :param line:      sale.order.line record
        :param meter_uom: cached uom.uom record for meters
        :return: float — weight in kg per piece
        """
        weight_per_uom = product.weight or 0.0
        if not weight_per_uom or not line.d1_length:
            return weight_per_uom
        # Check if the product's UoM belongs to the Length tree.
        if not product.uom_id._has_common_reference(meter_uom):
            return weight_per_uom
        # Convert d1_length (meters) → product UoM and multiply.
        length_in_prod_uom = meter_uom._compute_quantity(
            line.d1_length, product.uom_id, round=False,
        )
        return weight_per_uom * length_in_prod_uom

    @staticmethod
    def _d1_piece_qty(product, line):
        """Return the number of pieces for an order line.

        When ``d1_use_qty`` is active, ``product_uom_qty`` is total UoM
        units (e.g. total meters), so we use ``d1_qty`` (actual piece
        count) instead.
        """
        if product.d1_use_qty and line.d1_qty:
            return line.d1_qty
        return line.product_uom_qty

    # ------------------------------------------------------------------
    # TK1 — Bundle calculation (long products / tubes)
    # ------------------------------------------------------------------

    def _d1_compute_tk1(self, lines):
        """Calculate transport cost for TK1 (bundles) with weight banding.

        Weight banding per piece (applied before bundle calculation):
        - piece_weight >= max_kg         → entire TK1 → pallet (manual).
        - max_kg/2 <= piece_weight < max_kg → one-per-bundle pool (qty = bundles).
        - piece_weight < max_kg/2        → normal geometric calculation pool.
        Total bundles = one-per-bundle pool + normal pool.

        Returns: (cost, message_string, is_manual_flag, carrier_id)
        """
        self.ensure_one()
        class_id = self._d1_get_class_id("tk1")
        meter_uom = self.env.ref("uom.product_uom_meter")

        # Config parameters
        bundle_w = self._d1_get_param_float("d1_shipping.bundle_width_cm", 15.0)
        bundle_h = self._d1_get_param_float("d1_shipping.bundle_height_cm", 15.0)
        bundle_max_kg = self._d1_get_param_float("d1_shipping.bundle_max_weight_kg", 20.0)
        half_max_kg = bundle_max_kg / 2.0
        tk1_max_bundles = self._d1_get_param_int("d1_shipping.tk1_max_bundels", 99999)

        # --- Step 1: Weight banding — split lines into pools ---
        pool_one_per = []   # (product, qty) — mid-band: one piece per bundle
        pool_normal = []    # (product, qty) — light band: normal geometric calc
        max_length_cm = 0.0
        details = []

        for line in lines:
            prod = line.product_id
            piece_weight = self._d1_piece_weight(prod, line, meter_uom)
            qty = self._d1_piece_qty(prod, line)
            # Use order line length (may differ from product if user overrides).
            # d1_length is in meters; convert to cm for bracket lookup.
            if line.d1_length:
                length_cm = line.d1_length * 100.0
            else:
                length_cm = prod.d1_length_cm or 0.0

            if length_cm > max_length_cm:
                max_length_cm = length_cm

            # Heavy band: piece >= max → entire TK1 class = pallet
            if piece_weight >= bundle_max_kg:
                msg = (
                    "TK1: product '%s' weegt %.2f kg/stuk (>= %.0f kg max bundel) "
                    "→ PALLETBEREKENING (handmatig)."
                    % (prod.display_name, piece_weight, bundle_max_kg)
                )
                _logger.info(
                    "Order %s: TK1 pallet — product '%s' piece weight %.2f >= %.0f",
                    self.name, prod.display_name, piece_weight, bundle_max_kg,
                )
                return 0.0, msg, True, False

            # Mid band: max/2 <= piece < max → one piece per bundle
            if piece_weight >= half_max_kg:
                pool_one_per.append({"product": prod, "qty": qty})
                details.append(
                    "  %s: %d stuks × 1/bundel (%.2f kg/stuk, één-per-bundel)"
                    % (prod.display_name, int(qty), piece_weight)
                )
            else:
                # Light band (incl. weight == 0): normal geometric calculation
                pool_normal.append({"product": prod, "qty": qty, "piece_weight": piece_weight})

        # --- Step 2: One-per-bundle pool ---
        bundles_one_per = sum(int(p["qty"]) for p in pool_one_per)

        # --- Step 3: Normal geometric pool (existing logic) ---
        bundles_normal = 0

        # Compute total weight from pool entries (piece_weight already
        # accounts for length when the product is sold by the meter).
        total_weight_light = sum(p["qty"] * p["piece_weight"] for p in pool_normal)

        # Group normal-pool by product for geometric calculation
        normal_by_product = {}
        for p in pool_normal:
            pid = p["product"].id
            normal_by_product.setdefault(pid, {"product": p["product"], "qty": 0})
            normal_by_product[pid]["qty"] += p["qty"]

        for pdata in normal_by_product.values():
            prod = pdata["product"]
            qty = pdata["qty"]
            w = prod.d1_width_cm or 0.0
            h = prod.d1_height_cm or 0.0

            # Tubes fitting in the bundle cross-section
            tubes_w = max(int(bundle_w // w), 1) if w > 0 else 1
            tubes_h = max(int(bundle_h // h), 1) if h > 0 else 1
            tubes_per_bundle = tubes_w * tubes_h

            prod_bundles = math.ceil(qty / tubes_per_bundle) if tubes_per_bundle > 0 else math.ceil(qty)
            bundles_normal += prod_bundles

            details.append(
                "  %s: %d stuks, %d/bundel → %d bundels (normaal)"
                % (prod.display_name, int(qty), tubes_per_bundle, prod_bundles)
            )

        # Weight correction on the normal (light) pool only
        bundles_preliminary = bundles_normal
        if bundles_normal > 0 and total_weight_light > 0:
            if total_weight_light / bundles_normal >= bundle_max_kg:
                bundles_normal = math.ceil(total_weight_light / bundle_max_kg)

        # --- Step 4: Total bundles = both pools ---
        total_bundles = bundles_one_per + bundles_normal

        # --- Step 5: Threshold & rate lookup (unchanged tail) ---
        if total_bundles >= tk1_max_bundles:
            msg = (
                "TK1: %d bundels >= drempel (%d) → PALLETBEREKENING (handmatig).\n"
                "  (%d één-per-bundel + %d normaal)\n%s"
                % (total_bundles, tk1_max_bundles, bundles_one_per, bundles_normal,
                   "\n".join(details))
            )
            _logger.info("Order %s: TK1 pallet threshold reached (%d bundles)", self.name, total_bundles)
            return 0.0, msg, True, False

        # Determine length bracket from max length across ALL TK1 lines (both pools)
        bracket = self._d1_find_length_bracket(max_length_cm)
        bracket_label = bracket.name if bracket else "onbekend"
        bracket_id = bracket.id if bracket else False

        if not bracket:
            msg = (
                "TK1: %d bundels, max lengte %.0f cm — GEEN LENGTEKLASSE GEVONDEN, "
                "handmatig bepalen.\n%s"
                % (total_bundles, max_length_cm, "\n".join(details))
            )
            return 0.0, msg, True, False

        price, carrier_id = self._d1_find_rate(class_id, total_bundles, length_bracket_id=bracket_id)

        if price == 0.0:
            msg = (
                "TK1: %d bundels, lengteklasse %s — GEEN TARIEF GEVONDEN voor afleveradres, handmatig bepalen.\n%s"
                % (total_bundles, bracket_label, "\n".join(details))
            )
            return 0.0, msg, True, False

        weight_corrected = bundles_normal != bundles_preliminary
        msg = (
            "TK1: %d bundels (%d één-per-bundel + %d normaal%s), "
            "max lengte %.0f cm (%s), tarief € %.2f.\n%s"
            % (
                total_bundles,
                bundles_one_per,
                bundles_normal,
                ", gewichtscorrectie" if weight_corrected else "",
                max_length_cm,
                bracket_label,
                price,
                "\n".join(details),
            )
        )
        return price, msg, False, carrier_id

    # ------------------------------------------------------------------
    # TK2 — Box calculation (by weight)
    # ------------------------------------------------------------------

    def _d1_compute_tk2(self, lines):
        """Calculate transport cost for TK2 (boxes by weight) with weight banding.

        Weight banding per piece (applied before box calculation):
        - piece_weight >= max_kg         → entire TK2 → pallet (manual).
        - max_kg/2 <= piece_weight < max_kg → one-per-box pool (qty = boxes).
        - piece_weight < max_kg/2        → normal weight-sum pool.
        Total boxes = one-per-box pool + normal pool.

        Returns: (cost, message_string, is_manual_flag, carrier_id)
        """
        self.ensure_one()
        class_id = self._d1_get_class_id("tk2")
        meter_uom = self.env.ref("uom.product_uom_meter")

        tk2_max_kg = self._d1_get_param_float("d1_shipping.tk2_max_gewicht_kg", 99999.0)
        box_max_kg = self._d1_get_param_float("d1_shipping.box_max_weight_kg", 20.0)
        if box_max_kg <= 0:
            box_max_kg = 20.0
        half_max_kg = box_max_kg / 2.0

        # --- Step 1: Overall weight threshold ---
        total_weight = sum(
            self._d1_piece_qty(l.product_id, l)
            * self._d1_piece_weight(l.product_id, l, meter_uom)
            for l in lines
        )
        if total_weight >= tk2_max_kg:
            msg = (
                "TK2: totaal gewicht %.2f kg >= drempel %.0f kg → PALLETBEREKENING (handmatig)."
                % (total_weight, tk2_max_kg)
            )
            _logger.info("Order %s: TK2 pallet threshold reached (%.2f kg)", self.name, total_weight)
            return 0.0, msg, True, False

        # --- Step 2: Weight banding per piece ---
        boxes_one_per = 0
        light_weight = 0.0
        details = []

        for line in lines:
            prod = line.product_id
            piece_weight = self._d1_piece_weight(prod, line, meter_uom)
            qty = self._d1_piece_qty(prod, line)

            # Heavy band: piece >= max → entire TK2 class = pallet
            if piece_weight >= box_max_kg:
                msg = (
                    "TK2: product '%s' weegt %.2f kg/stuk (>= %.0f kg max doos) "
                    "→ PALLETBEREKENING (handmatig)."
                    % (prod.display_name, piece_weight, box_max_kg)
                )
                _logger.info(
                    "Order %s: TK2 pallet — product '%s' piece weight %.2f >= %.0f",
                    self.name, prod.display_name, piece_weight, box_max_kg,
                )
                return 0.0, msg, True, False

            # Mid band: max/2 <= piece < max → one piece per box
            if piece_weight >= half_max_kg:
                boxes_one_per += int(qty)
                details.append(
                    "  %s: %d stuks × 1/doos (%.2f kg/stuk, één-per-doos)"
                    % (prod.display_name, int(qty), piece_weight)
                )
            else:
                # Light band (incl. weight == 0): sum weight for normal box calc
                light_weight += qty * piece_weight
                if piece_weight > 0:
                    details.append(
                        "  %s: %d stuks × %.2f kg = %.2f kg (normaal)"
                        % (prod.display_name, int(qty), piece_weight, qty * piece_weight)
                    )

        # --- Step 3 & 4: Normal pool box count + total ---
        boxes_normal = math.ceil(light_weight / box_max_kg) if light_weight > 0 else 0
        total_boxes = boxes_one_per + boxes_normal

        if total_boxes == 0:
            return 0.0, "TK2: geen gewicht → € 0,00.", False, False

        # --- Step 5: Rate lookup ---
        price, carrier_id = self._d1_find_rate(class_id, total_boxes)

        if price == 0.0:
            msg = (
                "TK2: %d dozen (%d één-per-doos + %d normaal) "
                "— GEEN TARIEF GEVONDEN voor afleveradres, handmatig bepalen.\n%s"
                % (total_boxes, boxes_one_per, boxes_normal, "\n".join(details))
            )
            return 0.0, msg, True, False

        msg = (
            "TK2: %.2f kg → %d dozen (%d één-per-doos + %d normaal), "
            "tarief € %.2f.\n%s"
            % (total_weight, total_boxes, boxes_one_per, boxes_normal,
               price, "\n".join(details))
        )
        return price, msg, False, carrier_id

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

        Returns: (cost, message_string, is_manual_flag, carrier_id)
        """
        self.ensure_one()
        class_id = self._d1_get_class_id("tk3")
        meter_uom = self.env.ref("uom.product_uom_meter")

        # TODO (open punt): tk3_max_gewicht_kg drempelwaarde nog vast te stellen
        tk3_max_kg = self._d1_get_param_float("d1_shipping.tk3_max_gewicht_kg", 99999.0)
        box_max_kg = self._d1_get_param_float("d1_shipping.box_max_weight_kg", 20.0)

        total_weight = sum(
            self._d1_piece_qty(l.product_id, l)
            * self._d1_piece_weight(l.product_id, l, meter_uom)
            for l in lines
        )

        # --- Step 1: total weight threshold ---
        if total_weight >= tk3_max_kg:
            msg = (
                "TK3: totaal gewicht %.2f kg >= drempel %.0f kg → PALLETBEREKENING (handmatig)."
                % (total_weight, tk3_max_kg)
            )
            _logger.info("Order %s: TK3 pallet threshold reached (%.2f kg)", self.name, total_weight)
            return 0.0, msg, True, False

        # --- Step 2: per-article dimension/weight checks ---
        for line in lines:
            prod = line.product_id
            w_kg = self._d1_piece_weight(prod, line, meter_uom)
            length = prod.d1_length_cm or 0.0
            width = prod.d1_width_cm or 0.0
            height = prod.d1_height_cm or 0.0

            # 2a. Single article weight >= 20 kg → pallet
            if w_kg >= 20.0:
                msg = (
                    "TK3: product '%s' weegt %.2f kg (>= 20 kg) → PALLETBEREKENING (handmatig)."
                    % (prod.display_name, w_kg)
                )
                return 0.0, msg, True, False

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
                return 0.0, msg, True, False

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
                return 0.0, msg, True, False

        # --- Step 3: within limits → box calculation ---
        if box_max_kg <= 0:
            box_max_kg = 20.0
        num_boxes = math.ceil(total_weight / box_max_kg) if total_weight > 0 else 0

        if num_boxes == 0:
            return 0.0, "TK3: geen gewicht → € 0,00.", False, False

        price, carrier_id = self._d1_find_rate(class_id, num_boxes)

        if price == 0.0:
            msg = (
                "TK3: %d dozen (%.2f kg) — GEEN TARIEF GEVONDEN voor afleveradres, handmatig bepalen."
                % (num_boxes, total_weight)
            )
            return 0.0, msg, True, False

        msg = "TK3: %.2f kg → %d dozen, tarief € %.2f." % (total_weight, num_boxes, price)
        return price, msg, False, carrier_id

    # ------------------------------------------------------------------
    # Transport cost order line management
    # ------------------------------------------------------------------

    def _d1_set_transport_line(self, total_cost):
        """Remove existing transport line and add a new one with total_cost.

        Uses the delivery product from the selected carrier
        (delivery.carrier.product_id).  The carrier is set on the order
        by _d1_do_compute_transport before this method is called.
        """
        self.ensure_one()

        # Remove existing transport lines (identified by name marker)
        existing = self.order_line.filtered(
            lambda l: TRANSPORT_LINE_NAME_MARKER in (l.name or "")
        )
        if existing:
            existing.unlink()

        # Add new line (only if cost > 0)
        if total_cost <= 0:
            return

        carrier = self.carrier_id
        if not carrier or not carrier.product_id:
            raise UserError(
                _("No delivery carrier (or no product on the carrier) is set. "
                  "Cannot create the transport cost line.")
            )

        self.env["sale.order.line"].create({
            "order_id": self.id,
            "product_id": carrier.product_id.id,
            "name": "%s %s" % (TRANSPORT_LINE_NAME_MARKER, carrier.name),
            "product_uom_qty": 1,
            "price_unit": total_cost,
            "sequence": 9999,  # place at the end
        })
