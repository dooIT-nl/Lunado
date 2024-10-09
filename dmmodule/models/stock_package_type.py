from odoo import fields, models, api
from odoo.exceptions import UserError


class StockPackageType(models.Model):
    _inherit = 'stock.package.type'

    min_volume = fields.Float(string="Minimum Volume", digits='Volume')
    max_volume = fields.Float(compute="_compute_max_volume", string="Maximum Volume", digits='Volume')
    min_m2 = fields.Float(string="Minimum M2")
    max_m2 = fields.Float(compute="_compute_max_m2", string="Maximum M2")

    def get_max_m2(self):
        return (self.height * self.width) / 1_000_000

    def get_max_volume(self):
        return (self.height * self.width * self.packaging_length) / 1_000_000_000

    def attach_package_to_delivery(self):
        if len(self) < 1: raise UserError("Please select at least one shipping option to proceed")
        stock_picking_id = self.env.context.get('stock_picking_id')

        for selected_package in self: #selected_packages
            self.env["dm.package"].create({
                "height": selected_package.height / 10,
                "length": selected_package.packaging_length / 10,
                "width": selected_package.width / 10,
                "weight": selected_package.base_weight,
                "description": selected_package.name,
                "type": selected_package.barcode if selected_package.barcode else selected_package.name,
                "stock_picking_id": stock_picking_id,
            })

    @api.model
    def _compute_max_volume(self):
        for record in self:
            record.max_volume = record.get_max_volume()

    @api.model
    def _compute_max_m2(self):
        for record in self:
            record.max_m2 = record.get_max_m2()