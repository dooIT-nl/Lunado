import json

import odoo
import yaml
from odoo.http import route, request, NotFound
from werkzeug.exceptions import BadRequest


class Callback(odoo.http.Controller):
    @route('/deliverymatch/callback/<string:delivery_order_number>', auth='api_key', website=True, type='json', methods=['POST'])
    def handler(self, delivery_order_number):
        data = request.httprequest.data
        req = yaml.load(data, Loader=None)

        stock_picking = request.env["stock.picking"].search([("delivery_order_number", "=", delivery_order_number)])

        if not stock_picking:
            raise NotFound("No such sale")

        if ('status' not in req) or ('packages' not in req):
            raise BadRequest("Incorrect payload")

        if len(stock_picking.labels) == 0:
            for index, package in enumerate(req["packages"]):
                try:
                    stock_picking.write({"labels": [(0, 0, {
                        "label_url": package["labelURL"],
                        "barcode": package["barcode"],
                        "tracking_url": package["trackingURL"] if "trackingURL" in package else "",
                        "weight": package["weight"],
                        "length": package["length"],
                        "height": package["height"],
                        "width": package["width"],
                        "type": package["type"],
                        "description": package["description"],
                    })]})
                except IndexError:
                    stock_picking.write({"labels": [(0, 0, {
                        "label_url": package["labelURL"],
                        "barcode": package["barcode"],
                        "tracking_url": package["trackingURL"] if "trackingURL" in package else "",
                    })]})


        stock_move = request.env["stock.move"].search([("picking_id", "=", stock_picking.id)])

        if not stock_move: raise NotFound("No stock move not found.")

        for line in stock_move:
            line.write({"quantity_done": line.product_uom_qty})

        stock_picking.action_set_quantities_to_reservation()
        if not stock_picking._check_backorder():
            stock_picking.button_validate()

        stock_picking.dm_status = req['status']
        stock_picking.tracking_urls = req['labelURL'] if "labelURL" in req else ""

        return {"status": "success"}

    @route('/deliverymatch/callback/inbound/<string:delivery_order_number>', auth='api_key', website=True, type='json', methods=['POST'])
    def handleInbound(self, delivery_order_number):
        data = request.httprequest.data
        req = yaml.load(data, Loader=None)

        stock_picking = request.env["stock.picking"].search([("delivery_order_number", "=", delivery_order_number)])

        if not stock_picking: raise NotFound("No such sale")

        if "items" not in req.keys():
            raise BadRequest("No items provided in request body.")

        for item in req['items']:
            if "sku" not in item.keys() or "quantity" not in item.keys():
                continue

            product_template = request.env["product.template"].search([("dm_sku", "=", item['sku'])])

            if not product_template: continue

            product = request.env["product.product"].search([("product_tmpl_id", "=", product_template.id)])

            if not product: continue

            stock_move = request.env["stock.move"].search([("picking_id", "=", stock_picking.id), ("product_id", "=", product.id)], limit=1)

            if not stock_move: continue

            stock_move.write({"quantity_done": item['quantity']})


        return {"status": "success"}
