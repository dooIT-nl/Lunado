# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
from odoo import models, api, fields, _
from odoo.tools import float_compare
from odoo.http import request


class AccountMoveLine(models.Model):
    _inherit ="account.move.line"

    product_packaging_id = fields.Many2one(comodel_name='product.packaging', string="Packaging")


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.model
    def create(self, vals):
        res = super(StockMove, self).create(vals)
        if res.product_packaging_id:
            res.product_uom_qty = res.sale_line_id.product_uom_qty * res.product_packaging_id.qty or 1
        return res

    def _prepare_procurement_values(self):
        res = super(StockMove, self)._prepare_procurement_values()
        res.update({'product_uom_qty': res.sale_line_id.product_uom_qty * res.product_packaging_id.qty or 1})
        return res

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_qty = fields.Float(string="Packages Quantity",
        digits='Product Unit of Measure', default=1.0,
        store=True, readonly=False, required=True, precompute=True)

    @api.onchange('product_qty', 'product_uom_qty')
    def onchange_product_qty(self):
        if self.product_packaging_id and self.product_uom_qty:
            self.product_qty = self.product_uom_qty * self.product_packaging_id.qty

    def _prepare_procurement_values(self,group_id):
        res = super(SaleOrderLine,self)._prepare_procurement_values(group_id)
        res.update({
			'product_uom_qty' : self.product_uom_qty * self.product_packaging_id.qty,
		})
        return res

    
    def _prepare_invoice_line(self,**optional_values):
        res = super(SaleOrderLine,self)._prepare_invoice_line(**optional_values)
        if self.product_packaging_id:
            res.update({'product_packaging_id': self.product_packaging_id.id})
        return res

    def _compute_qty_delivered(self):
        res = super(SaleOrderLine, self)._compute_qty_delivered()
        for record in self:
            if record.product_packaging_id:
                record.qty_delivered = record.qty_delivered / record.product_packaging_id.qty
        return res

    def product_package_wizard(self):
        return {
            'name': "Add Package Product",
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'product.package.wizard',
            'view_id': self.env.ref('bi_website_package_pricelist.product_package_wizard_form').id,
            'context': {'default_product_tmpl_id': self.product_template_id.id},
            'target': 'new',
        }

    @api.onchange('product_uom_qty', 'product_packaging_id')
    def _onchange_product_id_package(self):
        res = self.env['res.config.settings'].sudo().search([], limit=1, order="id desc")
        if self.product_id and self.product_packaging_id:
            self.product_qty = self.product_packaging_id.qty * self.product_uom_qty
            if res.product_pricelist_setting == 'advanced':
                if self.product_packaging_id and self.order_id.pricelist_id:
                    price_id = self.order_id.pricelist_id.item_ids.filtered(lambda l: l.product_package_id == self.product_id and l.applied_on == '4_package' and l.package_id.id == self.product_packaging_id.id)
                    if price_id:
                        self.price_unit = self.order_id.pricelist_id.with_context(price_id=price_id)._get_product_price(self.product_id, self.product_uom_qty)
                    else:
                        if self.product_packaging_id and self.product_packaging_id.product_id:
                            self.price_unit = self.product_packaging_id.product_id.list_price

    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_price_unit(self):
        for line in self:
            if not line.product_packaging_id:
                if line.qty_invoiced > 0:
                    continue
                if not line.product_uom or not line.product_id or not line.order_id.pricelist_id:
                    line.price_unit = 0.0
                else:
                    price = line.with_company(line.company_id)._get_display_price()
                    line.price_unit = line.product_id._get_tax_included_unit_price(
                        line.company_id,
                        line.order_id.currency_id,
                        line.order_id.date_order,
                        'sale',
                        fiscal_position=line.order_id.fiscal_position_id,
                        product_price_unit=price,
                        product_currency=line.currency_id
                    )

    @api.depends('product_id', 'product_uom_qty', 'product_uom')
    def _compute_product_packaging_id(self):
        for line in self:
            if line.product_packaging_id.product_id != line.product_id:
                line.product_packaging_id = False

    @api.depends('display_type', 'product_id', 'product_packaging_qty')
    def _compute_product_uom_qty(self):
        for line in self:
            if line.display_type:
                line.product_uom_qty = 0.0
                continue
            if not line.product_packaging_id:
                continue
            packaging_uom = line.product_packaging_id.product_uom_id
            qty_per_packaging = line.product_packaging_id.qty
            product_uom_qty = packaging_uom._compute_quantity(
                line.product_packaging_qty * qty_per_packaging, line.product_uom)
            if float_compare(product_uom_qty, line.product_uom_qty, precision_rounding=line.product_uom.rounding) != 0:
                if not line.product_packaging_id:
                    line.product_uom_qty = product_uom_qty
