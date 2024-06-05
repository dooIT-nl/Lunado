from odoo import fields, models, api


class StockPackageType(models.Model):
    _inherit = 'stock.package.type'

    min_volume = fields.Float(string="Minimum Volume", digits='Volume')
    max_volume = fields.Float(compute="_compute_max_volume", string="Maximum Volume", digits='Volume')

    def get_max_volume(self):
        return (self.height * self.width * self.packaging_length) / 1_000_000_000

    @api.model
    def _compute_max_volume(self):
        for record in self:
            record.max_volume = record.get_max_volume()