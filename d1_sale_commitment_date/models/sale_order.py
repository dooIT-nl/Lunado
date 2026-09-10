import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


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
            dates = [
                line._d1_get_expected_date() for line in order.order_line
            ]
            dates = [d for d in dates if d]
            computed = max(dates) if dates else False
            order.d1_computed_commitment_date = computed
            commitment = computed
            request = order.d1_customer_request_date
            if request and (not computed or request > computed):
                commitment = request
            order.commitment_date = commitment or order.commitment_date

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
