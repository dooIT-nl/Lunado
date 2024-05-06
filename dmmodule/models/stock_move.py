import logging

from odoo import models


class StockMove(models.Model):
    # name="dm.sale.order"
    _inherit = "stock.move"
    _logger = logging.getLogger("stock.move")

    def as_deliverymatch_packages(self, combined_qty = None, combined_weight = None):
        product = self.product_id
        packaging = self.env["product.packaging"].search([("product_id", "=", product.id)], order="qty desc")

        if not packaging:
            return None

        amount_in_box = self.product_uom_qty
        remaining_quantity = amount_in_box if combined_qty is None else combined_qty
        packages = []
        attempts = 0
        while remaining_quantity > 0 and attempts <= 50:
            for package in packaging:
                if not package.id:
                    continue
                package_max_qty = package.qty
                if remaining_quantity >= package.min_qty and (remaining_quantity > package_max_qty or remaining_quantity <= package_max_qty):
                    package_type = package.package_type_id
                    remaining_quantity -= amount_in_box
                    weight_in_box = amount_in_box * self.product_tmpl_id.weight
                    packages.append({
                        "type": package_type.barcode,
                        "description": package_type.name,
                        "height": package_type.height,
                        "width": package_type.width,
                        "length": package_type.packaging_length,
                        "weight": weight_in_box if combined_weight is None else combined_weight / amount_in_box,
                    })
                    continue

            attempts += 1

        return packages