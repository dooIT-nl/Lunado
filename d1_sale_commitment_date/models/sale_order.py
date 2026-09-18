import logging
from datetime import timedelta

import pytz
from markupsafe import Markup, escape

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

DEFAULT_CUTOFF_PARAM = "d1_sale_commitment_date.default_cutoff_hour"


class SaleOrder(models.Model):
    _inherit = "sale.order"

    commitment_date = fields.Datetime(
        compute="_compute_d1_commitment_date",
        store=True,
        readonly=False,
    )
    d1_customer_request_date = fields.Datetime(
        string="Customer Requested Date",
        help="Delivery date requested by the customer. If it is later than "
        "the computed delivery date, it is used as the delivery date. If it "
        "is earlier, a warning is shown and the computed date is kept.",
    )
    d1_computed_commitment_date = fields.Datetime(
        string="Computed Delivery Date",
        compute="_compute_d1_commitment_date",
        store=True,
        help="Earliest possible delivery date computed from the order lines "
        "(free stock, next planned receipt or customer lead time).",
    )
    d1_delivery_date_warning = fields.Boolean(
        compute="_compute_d1_delivery_date_warning",
    )

    @api.depends(
        "order_line.product_id",
        "order_line.product_uom_qty",
        "order_line.product_uom_id",
        "warehouse_id",
        "d1_customer_request_date",
        "partner_id",
    )
    def _compute_d1_commitment_date(self):
        """Bereken de leverdatum van de order uit de orderregels.

        Per regel wordt de vroegst mogelijke datum bepaald (zie
        sale.order.line._d1_get_expected_date); de laatste regeldatum is de
        eerst mogelijke leverdatum van de order (geen deelleveringen).
        Een gewenste leverdatum van de klant die later valt dan de berekende
        datum wordt overgenomen als leverdatum. Bevestigde orders worden niet
        meer herberekend.
        """
        for order in self:
            if order.state not in ("draft", "sent"):
                # Keep values on confirmed/locked/cancelled orders.
                order.commitment_date = order.commitment_date
                order.d1_computed_commitment_date = (
                    order.d1_computed_commitment_date
                )
                continue
            dates = []
            explanations = []
            for line in order.order_line:
                date, expl = line._d1_get_expected_date_explained()
                if date:
                    dates.append(date)
                explanations.extend(expl)
            computed_raw = max(dates) if dates else False
            # LUN-9/10: round the final date to the next working day, taking
            # the (per-customer) cutoff time into account.
            computed = order._d1_round_to_working_day(computed_raw)
            if computed_raw and computed != computed_raw:
                explanations.append(
                    "Werkdag-/cutoff-afronding: %s → %s (cutoff %05.2f uur)"
                    % (computed_raw, computed, order._d1_get_cutoff_hour())
                )
            order.d1_computed_commitment_date = computed
            commitment = computed
            request = order.d1_customer_request_date
            if request and (not computed or request > computed):
                commitment = order._d1_round_to_working_day(request)
                explanations.append(
                    "Gewenste klantdatum %s is later dan berekend → "
                    "overgenomen als leverdatum" % request
                )
            elif request and computed and request < computed:
                explanations.append(
                    "Gewenste klantdatum %s is eerder dan berekend %s → "
                    "berekende datum blijft (banner)" % (request, computed)
                )
            order.commitment_date = commitment or order.commitment_date
            order._d1_post_explanation(explanations)

    def _d1_post_explanation(self, explanations):
        """Plaats (tijdelijk, diagnostisch) een chatternotitie die uitlegt
        hoe de leverdatum is berekend.

        Alleen actief zolang de systeemparameter
        d1_sale_commitment_date.explain op '1' staat; uitzetten = geen
        meldingen meer, zonder code-wijziging. Wordt overgeslagen tijdens
        onchange (record bestaat nog niet). Teksten bewust onvertaald
        (tijdelijk diagnose-instrument).
        """
        self.ensure_one()
        if not explanations or not isinstance(self.id, int):
            return
        # sudo: systeemparameter is niet leesbaar voor gewone gebruikers;
        # read-only diagnosevlag.
        if self.env["ir.config_parameter"].sudo().get_param(
            "d1_sale_commitment_date.explain"
        ) != "1":
            return
        body = Markup(
            "<b>Leverdatum-berekening</b> (tijdelijke diagnose)<br/>%s"
            "<br/><b>Leverdatum: %s</b>"
        ) % (
            Markup("<br/>").join(escape(e) for e in explanations),
            self.commitment_date or "-",
        )
        try:
            self.message_post(
                body=body, subtype_xmlid="mail.mt_note",
            )
        except Exception:
            _logger.warning(
                "d1_sale_commitment_date: could not post explanation on %s",
                self.display_name, exc_info=True,
            )

    def _d1_get_cutoff_hour(self):
        """Bepaal de cutoff-tijd (in uren, bv. 16.5 = 16:30) voor deze order.

        Volgorde: cutoff op de klant (res.partner), anders de systeem-default
        uit ir.config_parameter (d1_sale_commitment_date.default_cutoff_hour),
        anders 0.0 = geen cutoff (overgang naar de volgende werkdag om
        middernacht).

        :return: float cutoff-uur (0.0 = geen cutoff)
        """
        self.ensure_one()
        cutoff = self.partner_id.d1_delivery_cutoff_hour
        if not cutoff:
            # sudo: system parameters are not readable for regular users;
            # this is a harmless read-only configuration value.
            param = (
                self.env["ir.config_parameter"]
                .sudo()
                .get_param(DEFAULT_CUTOFF_PARAM, "0")
            )
            try:
                cutoff = float(param)
            except ValueError:
                _logger.warning(
                    "Invalid value %r for %s, using 0.0",
                    param,
                    DEFAULT_CUTOFF_PARAM,
                )
                cutoff = 0.0
        return cutoff

    def _d1_round_to_working_day(self, dt):
        """Rond een berekende leverdatum af op de eerstvolgende werkdag.

        Regels (klantbesluit LUN-9/10):
        * Valt het tijdstip op of na de cutoff-tijd van de klant, dan
          verschuift de levering een dag (cutoff 0.0 = geen verschuiving,
          de dag loopt dan tot middernacht).
        * Weekenddagen (za/zo) schuiven door naar maandag.
        * De tijd-component blijft behouden; alleen de dag verschuift.
        * Beoordeling gebeurt in de tijdzone van de klant (anders bedrijf,
          anders UTC); opslag blijft UTC.

        :param dt: naive UTC datetime of False
        :return: afgeronde naive UTC datetime, of ongewijzigd False
        """
        self.ensure_one()
        if not dt:
            return dt
        tz_name = (
            self.partner_id.tz
            or self.company_id.partner_id.tz
            or "UTC"
        )
        try:
            tz = pytz.timezone(tz_name)
        except pytz.UnknownTimeZoneError:
            _logger.warning("Unknown timezone %r, falling back to UTC", tz_name)
            tz = pytz.utc
        local = pytz.utc.localize(dt).astimezone(tz)
        cutoff = self._d1_get_cutoff_hour()
        if cutoff and (local.hour + local.minute / 60.0) >= cutoff:
            local += timedelta(days=1)
        while local.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
            local += timedelta(days=1)
        return local.astimezone(pytz.utc).replace(tzinfo=None)

    @api.onchange("commitment_date", "expected_date")
    def _onchange_commitment_date(self):
        """Onderdruk de standaard 'Gevraagde datum is te snel'-melding.

        Standaard Odoo vergelijkt de leverdatum met expected_date (orderdatum
        + sale_delay). Onze berekening negeert de sale_delay bewust bij
        voldoende voorraad, waardoor die melding bij elk voorradig product
        met een levertijd onterecht zou verschijnen. Zolang deze module de
        leverdatum berekent (d1_computed_commitment_date gevuld) is de
        standaardmelding daarom uitgeschakeld; de eigen waarschuwingsbanner
        dekt het geval 'klant wil eerder dan haalbaar'.
        """
        if self.d1_computed_commitment_date:
            return None
        return super()._onchange_commitment_date()

    @api.depends("d1_customer_request_date", "d1_computed_commitment_date")
    def _compute_d1_delivery_date_warning(self):
        """Waarschuw als de klant eerder wil leveren dan mogelijk is."""
        for order in self:
            order.d1_delivery_date_warning = bool(
                order.d1_customer_request_date
                and order.d1_computed_commitment_date
                and order.d1_customer_request_date
                < order.d1_computed_commitment_date
            )
