import logging
from datetime import timedelta

from odoo import fields, models

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _d1_get_expected_date(self):
        """Bereken de vroegst mogelijke leverdatum voor deze orderregel.

        Regels (per product):
        1. Voldoende vrije voorraad beschikbaar -> geen levertijd (nu).
        2. Onvoldoende voorraad -> scheduled_date van de eerstvolgende
           geplande ontvangst (stock.picking, incoming) met dit product.
        3. Geen geplande ontvangst -> nu + sale_delay van het product.

        Kit-/productieartikelen (stuklijst van type phantom of normal) worden
        geexplodeerd: de componenten worden elk volgens dezelfde regels
        berekend (benodigd aantal = aantal stuklijstregel x aantal op de
        orderregel). De laatste componentdatum bepaalt de regeldatum.

        :return: datetime van de vroegst mogelijke levering, of False als er
                 geen product op de regel staat.
        """
        self.ensure_one()
        product = self.product_id
        if not product or self.display_type:
            return False
        qty = self.product_uom_id._compute_quantity(
            self.product_uom_qty, product.uom_id
        )
        components = self._d1_explode_bom(product, qty)
        dates = [
            self._d1_get_product_expected_date(comp_product, comp_qty)
            for comp_product, comp_qty in components
        ]
        dates = [d for d in dates if d]
        return max(dates) if dates else False

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
        """Bereken de vroegst mogelijke leverdatum voor een (product, aantal).

        Zie _d1_get_expected_date voor de regels. Niet-voorraadgehouden
        producten (diensten e.d.) volgen enkel de sale_delay van het product.

        :param product: product.product record
        :param qty: benodigd aantal in de uom van het product
        :return: datetime van de vroegst mogelijke levering
        """
        self.ensure_one()
        now = fields.Datetime.now()
        if not product.is_storable:
            return now + timedelta(days=product.sale_delay or 0.0)
        warehouse = self.order_id.warehouse_id
        free_qty = product.with_context(
            warehouse=warehouse.id, warehouse_id=warehouse.id
        ).free_qty
        if free_qty >= qty:
            return now
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
            return picking.scheduled_date
        return now + timedelta(days=product.sale_delay or 0.0)
