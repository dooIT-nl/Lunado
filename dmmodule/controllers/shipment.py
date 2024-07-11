import json

from odoo.http import request, route, Controller, Response


class ShipmentController(Controller):
    @route('/deliverymatch/shipment/rates/<int:sale_id>', auth='user', type='http')
    def product_catalog_get_order_lines_info(self, sale_id, **kwargs):
        # get the information using the SUPER USER
        sale_order = request.env["sale.order"].search([("id", "=", sale_id)])

        if not sale_order:
            return Response(json.dumps({"message": f"sale.order with {sale_id} not found"}), content_type='application/json;charset=utf-8', status=404)


        return Response(json.dumps({"id": sale_order.as_deliverymatch_shipment()}), content_type='application/json;charset=utf-8',status=200)
