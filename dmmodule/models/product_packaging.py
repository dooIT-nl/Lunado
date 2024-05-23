import logging

from odoo import fields, models, api

class ProductPackaging(models.Model):
    _inherit = "product.packaging"
    _logger = logging.getLogger("product.packaging")

    min_qty = fields.Float(string="Minimum Contained Quantity")
    min_volume = fields.Float(string="Minimum Contained Volume m³")
    max_volume = fields.Float(compute="_compute_max_volume", string="Maximum Contained Volume m³")

    def get_max_volume(self):
        return (self.package_type_id.height * self.package_type_id.width * self.package_type_id.packaging_length) / 1_000_000

    @api.model
    def _compute_max_volume(self):
        for record in self:
            record.max_volume = record.get_max_volume()