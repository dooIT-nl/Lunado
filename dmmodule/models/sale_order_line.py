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

    def as_deliverymatch_packages(self, combined_products = None, combined_fragile_products = None):
        product = self.product_id
        product_template = self.product_template_id
        packaging = self.env["product.packaging"].search([("product_id", "=", product.id)], order="qty desc")

        if not packaging:
            return None

        is_combined = combined_products is not None
        is_combined_fragile = combined_fragile_products is not None
        is_fragile_product = product.dm_is_fragile
        is_fragile_package = is_combined_fragile or is_fragile_product

        product_quantity = self.set_product_quantity(is_fragile=is_fragile_package)

        if is_fragile_product:
            total_fragile_product_volume_in_m3 = product_template.get_area_in_m2(convert_to_m2=True) * product_quantity
            total_fragile_product_weight = product.weight * product_quantity

        if is_combined_fragile:
            total_fragile_product_volume_in_m3 = combined_fragile_products.get('volume') # quantity calculated in sale_order.py in method get_sales_order_lines_as_packages
            total_fragile_product_weight = combined_fragile_products.get('weight')

        if not is_combined and not is_fragile_package:
            remaining_quantity = product_quantity

        if is_combined and not is_fragile_package:
            remaining_quantity = combined_products['volume']

        if is_fragile_package and not is_combined:
            remaining_quantity = total_fragile_product_volume_in_m3

        packages = []
        attempts = 0

        while remaining_quantity > 0 and attempts <= 50:
            for package in packaging:
                if not package.id:
                    continue

                if not is_combined and not is_fragile_package:
                    package_min = package.min_qty
                    package_max = package.qty

                if is_combined:
                    package_min = package.package_type_id.min_volume
                    package_max = package.package_type_id.get_max_volume()

                if is_fragile_package:
                    package_min = package.package_type_id.min_m2
                    package_max = package.package_type_id.get_max_m2()

                if remaining_quantity > 0 and remaining_quantity >= package_min and (remaining_quantity > package_max or remaining_quantity <= package_max):
                    package_type = package.package_type_id
                    amount_in_box = self._calculate_amount_in_box(remaining_quantity, package_max)
                    remaining_quantity = round(remaining_quantity - amount_in_box, 8) # Rounding to 8 decimals to avoid tiny floating-point precision errors like 6.938893903907228e-18.
                    total_package_weight = amount_in_box * self.product_template_id.weight

                    if is_combined:
                        percentage_in_box = amount_in_box / combined_products['volume']
                        total_package_weight = percentage_in_box * combined_products['weight']

                    if is_fragile_package:
                        percentage_in_box = amount_in_box / total_fragile_product_volume_in_m3
                        total_package_weight = percentage_in_box * total_fragile_product_weight

                    packages.append({
                        "type": package_type.barcode if package_type.barcode else package.name,
                        "description": package_type.name,
                        "height": package_type.height,
                        "width": package_type.width,
                        "length": package_type.packaging_length,
                        "weight": total_package_weight,
                        "is_fragile_package": is_fragile_package
                    })
                    break  # breaks the packages for loop so that the loop restarts from the package with the highest qty

            attempts += 1

        return packages

    @staticmethod
    def _calculate_amount_in_box(remaining_quantity, max_package_qty):
        if remaining_quantity > max_package_qty:
            return max_package_qty

        return remaining_quantity

    def set_product_quantity(self, is_fragile:bool = False) -> float or int:
        quantity: float or int = self.product_uom_qty

        # MAATWERK LUNADO
        lunado_custom_qty:float or int = getattr(self, 'x_studio_qty', 0)
        if is_fragile and lunado_custom_qty != 0: quantity = lunado_custom_qty

        return quantity