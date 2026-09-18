import logging
from datetime import timedelta

from odoo import fields, models

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _d1_get_expected_date(self):
        """Bereken de vroegst mogelijke leverdatum voor deze orderregel.

        Zie _d1_get_expected_date_explained voor de regels; deze variant
        geeft alleen de datum terug.
        """
        return self._d1_get_expected_date_explained()[0]

    def _d1_get_expected_date_explained(self):
        """Bereken de vroegst mogelijke leverdatum voor deze orderregel en
        leg uit hoe die tot stand kwam.

        Regels (per product):
        1. Voldoende beschikbare voorraad (fysiek - bevestigde uitgaande
           vraag) -> geen levertijd (nu).
        2. Onvoldoende voorraad -> scheduled_date van de eerstvolgende
           geplande ontvangst (afgetopt op vandaag).
        3. Geen geplande ontvangst -> nu + sale_delay van het product.

        Kit-/productieartikelen worden geexplodeerd; de laatste
        componentdatum bepaalt de regeldatum.

        :return: tuple (datetime|False, list[str] uitleg-regels)
        """
        self.ensure_one()
        product = self.product_id
        if not product or self.display_type:
            return False, []
        qty = self.product_uom_id._compute_quantity(
            self.product_uom_qty, product.uom_id
        )
        explanations = []
        components = self._d1_explode_bom(product, qty)
        exploded = len(components) != 1 or components[0][0] != product
        if exploded:
            explanations.append(
                "%s: stuklijst geexplodeerd naar %d component(en):"
                % (product.display_name, len(components))
            )
        dates = []
        for comp_product, comp_qty in components:
            date, reason = self._d1_get_product_expected_date_explained(
                comp_product, comp_qty
            )
            if date:
                dates.append(date)
            prefix = " • " if exploded else ""
            explanations.append(prefix + reason)
        return (max(dates) if dates else False), explanations

    def _d1_explode_bom(self, product, qty):
        """Geef de te beoordelen (product, aantal)-paren voor een orderregel.

        Heeft het product een stuklijst van het type kit (phantom) of
        productie (normal), dan worden de stuklijstregels gebruikt. Het
        benodigde aantal per component = aantal van de stuklijstregel x het
        aantal kits/productieartikelen op de orderregel (bewust niet gedeeld
        door het aantal van de stuklijst-header, conform specificatie).

        :param product: product.product record
        :param qty: benodigd aantal in de uom van het product
        :return: lijst van (product.product, float qty) tuples
        """
        self.ensure_one()
        bom = self.env["mrp.bom"]._bom_find(
            product, company_id=self.company_id.id
        ).get(product)
        if not bom or bom.type not in ("phantom", "normal"):
            return [(product, qty)]
        components = []
        for bom_line in bom.bom_line_ids:
            if bom_line._skip_bom_line(product):
                continue
            comp_qty = bom_line.product_uom_id._compute_quantity(
                bom_line.product_qty, bom_line.product_id.uom_id
            )
            components.append((bom_line.product_id, comp_qty * qty))
        return components or [(product, qty)]

    def _d1_get_product_expected_date(self, product, qty):
        """Bereken de vroegst mogelijke leverdatum voor een (product, aantal);
        zie _d1_get_product_expected_date_explained."""
        return self._d1_get_product_expected_date_explained(product, qty)[0]

    def _d1_get_product_expected_date_explained(self, product, qty):
        """Bereken de vroegst mogelijke leverdatum voor een (product, aantal)
        en de uitleg daarbij.

        :param product: product.product record
        :param qty: benodigd aantal in de uom van het product
        :return: tuple (datetime, str uitleg)
        """
        self.ensure_one()
        now = fields.Datetime.now()
        name = product.display_name
        if not product.is_storable:
            date = now + timedelta(days=product.sale_delay or 0.0)
            return date, (
                "%s: geen voorraadproduct → levertijd %g dagen → %s"
                % (name, product.sale_delay or 0.0, date.date())
            )
        warehouse = self.order_id.warehouse_id
        product_wh = product.with_context(
            warehouse=warehouse.id, warehouse_id=warehouse.id
        )
        available = product_wh.qty_available - product_wh.outgoing_qty
        if available >= qty:
            return now, (
                "%s: voldoende voorraad (beschikbaar %g, nodig %g) → "
                "direct leverbaar (levertijd genegeerd)"
                % (name, available, qty)
            )
        picking = self.env["stock.picking"].search(
            [
                ("picking_type_id.code", "=", "incoming"),
                ("picking_type_id.warehouse_id", "=", warehouse.id),
                ("state", "not in", ("done", "cancel")),
                ("move_ids.product_id", "=", product.id),
                ("company_id", "=", self.order_id.company_id.id),
            ],
            order="scheduled_date asc",
            limit=1,
        )
        if picking:
            # LUN-3: verlate ontvangsten aftoppen op vandaag
            date = max(picking.scheduled_date, now)
            clamped = (
                " (verlate ontvangst, afgetopt op vandaag)"
                if picking.scheduled_date < now else ""
            )
            return date, (
                "%s: onvoldoende voorraad (beschikbaar %g, nodig %g) → "
                "eerstvolgende ontvangst %s op %s%s"
                % (name, available, qty, picking.name,
                   date.date(), clamped)
            )
        date = now + timedelta(days=product.sale_delay or 0.0)
        return date, (
            "%s: onvoldoende voorraad (beschikbaar %g, nodig %g), geen "
            "geplande ontvangst → levertijd %g dagen → %s"
            % (name, available, qty, product.sale_delay or 0.0, date.date())
        )
