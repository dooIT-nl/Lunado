import logging

from odoo import models


class StockMove(models.Model):
    # name="dm.sale.order"
    _inherit = "stock.move"
    _logger = logging.getLogger("stock.move")

    def as_deliverymatch_packages(self, combined_products = None):
        product = self.product_id
        packaging = self.env["product.packaging"].search([("product_id", "=", product.id)], order="qty desc")

        if not packaging:
            return None

        is_combined = combined_products is not None
        remaining_quantity = self.product_uom_qty if not is_combined else combined_products['volume']
        packages = []
        attempts = 0

        while remaining_quantity > 0 and attempts <= 20:
            for package in packaging:
                if not package.id:
                    continue

                package_max = package.qty if not is_combined else package.package_type_id.get_max_volume()
                package_min = package.min_qty if not is_combined else package.package_type_id.min_volume
                if remaining_quantity > 0 and remaining_quantity >= package_min and (remaining_quantity > package_max or remaining_quantity <= package_max):
                    package_type = package.package_type_id
                    amount_in_box = self._calculate_amount_in_box(remaining_quantity, package_max)
                    remaining_quantity = remaining_quantity - amount_in_box
                    total_package_weight = amount_in_box * self.product_tmpl_id.weight

                    if is_combined:
                        percentage_in_box = amount_in_box / combined_products['volume']
                        total_package_weight = percentage_in_box * combined_products['weight']

                    packages.append({
                        "type": package_type.barcode if package_type.barcode else package.name,
                        "description": package_type.name,
                        "height": package_type.height,
                        "width": package_type.width,
                        "length": package_type.packaging_length,
                        "weight": total_package_weight,
                    })
                    continue

            attempts += 1

        return packages

    @staticmethod
    def _calculate_amount_in_box(remaining_quantity, max_package_qty):
        if remaining_quantity > max_package_qty:
            return max_package_qty

        return remaining_quantity
