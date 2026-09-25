import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    d1_credit_limit_exceeded = fields.Boolean(
        string="Credit Limit Exceeded",
        compute="_compute_d1_credit_limit_exceeded",
        help="The invoice partner's total receivable exceeds their credit "
        "limit.",
    )
    d1_exceed_credit_limit = fields.Boolean(
        string="Allow Exceeding Credit Limit",
        copy=False,
        help="Allow confirming this order even though the customer's credit "
        "limit is exceeded.",
    )

    @api.depends(
        "partner_invoice_id.credit",
        "partner_invoice_id.credit_limit",
    )
    def _compute_d1_credit_limit_exceeded(self):
        """Bepaal of het openstaande saldo van de factuurklant boven de
        kredietlimiet ligt. Niet stored: het saldo wijzigt buiten de order om,
        dus de waarde wordt altijd actueel berekend."""
        for order in self:
            partner = order.partner_invoice_id
            order.d1_credit_limit_exceeded = bool(
                partner
                and partner.credit_limit > 0
                and partner.credit > partner.credit_limit
            )

    @api.onchange("client_order_ref", "partner_id")
    def _onchange_d1_client_order_ref(self):
        """Directe melding bij invoer van een al gebruikte klantreferentie.

        Niet-blokkerend; de blokkade zelf zit in de constraint zodat ook
        API-aanroepen worden afgevangen.
        """
        if not self.client_order_ref or not self.partner_id:
            return
        duplicate = self._d1_find_duplicate_client_order_ref()
        if duplicate:
            return {
                "warning": {
                    "title": _("Duplicate customer reference"),
                    "message": _(
                        "The entered customer reference is already "
                        "registered for this customer (order %s).",
                        duplicate.display_name,
                    ),
                }
            }

    @api.constrains("partner_id")
    def _check_d1_partner_not_prospect(self):
        """Blokkeer verkooporders voor relaties van het type Prospect
        (pariteit met de Studio-automation 'Relatie is Prospect')."""
        for order in self:
            if order.partner_id.d1_rel_type == "prospect":
                raise ValidationError(
                    _(
                        "Warning: the selected customer %s is of type "
                        "Prospect! Change the relation type to Customer "
                        "before creating a sale order.",
                        order.partner_id.display_name,
                    )
                )

    @api.constrains("client_order_ref", "partner_id")
    def _check_d1_duplicate_client_order_ref(self):
        """Blokkeer een klantreferentie die al op een andere order van
        dezelfde klant is gebruikt (geldt voor alle gebruikers, besluit
        17-09-2026)."""
        for order in self:
            if not order.client_order_ref:
                continue
            duplicate = order._d1_find_duplicate_client_order_ref()
            if duplicate:
                raise ValidationError(
                    _(
                        "The entered customer reference is already "
                        "registered for this customer (order %s).",
                        duplicate.display_name,
                    )
                )

    def action_confirm(self):
        """Blokkeer bevestiging als de kredietlimiet van de factuurklant is
        overschreden en 'Overschrijding toestaan' niet is aangevinkt
        (pariteit met de Studio-automation 'Kredietlimiet')."""
        for order in self:
            if order.d1_credit_limit_exceeded and not order.d1_exceed_credit_limit:
                raise UserError(
                    _(
                        "Warning: the credit limit of %(partner)s has been "
                        "exceeded (outstanding %(credit).2f, limit "
                        "%(limit).2f). Check 'Allow Exceeding Credit Limit' "
                        "to confirm anyway.",
                        partner=order.partner_invoice_id.display_name,
                        credit=order.partner_invoice_id.credit,
                        limit=order.partner_invoice_id.credit_limit,
                    )
                )
        return super().action_confirm()

    def _d1_find_duplicate_client_order_ref(self):
        """Zoek een andere order van dezelfde klant met dezelfde
        klantreferentie. Retourneert maximaal 1 sale.order record."""
        self.ensure_one()
        return self.search(
            [
                ("partner_id", "=", self.partner_id.id),
                ("client_order_ref", "=", self.client_order_ref),
                ("id", "!=", self._origin.id or self.id),
            ],
            limit=1,
        )
