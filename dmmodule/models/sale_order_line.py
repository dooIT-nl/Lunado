import logging

from odoo import fields, models

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    _logger = logging.getLogger("DeliveryMatch - SaleOrderLine")


    def as_deliverymatch_product(self):
        template = self.product_template_id

        return {
            "content": self.name,
            "description": self.name,
            "weight": template.weight
        }

    def as_deliverymatch_packages(self, combined_qty = None, combined_weight = None):
        product = self.product_id
        packaging = self.env["product.packaging"].search([("product_id", "=", product.id)], order="qty desc")

        if not packaging:
            return None

        remaining_quantity = self.product_uom_qty if combined_qty is None else combined_qty
        packages = []
        attempts = 0
        while remaining_quantity > 0 and attempts <= 10:
            for package in packaging:
                if not package.id:
                    continue

                if remaining_quantity > package.min_qty and (remaining_quantity > package.qty or remaining_quantity <= package.qty):
                    package_type = package.package_type_id
                    amount_in_box = package.qty
                    remaining_quantity -= amount_in_box
                    weight_in_box = amount_in_box * self.product_template_id.weight
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