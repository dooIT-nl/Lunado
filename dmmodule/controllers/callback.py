import json

import odoo
import yaml
from odoo.http import route, request, NotFound
from werkzeug.exceptions import BadRequest
from ..models import helper
import logging


class Callback(odoo.http.Controller):
    _logger = logging.getLogger("DeliveryMatch - Callback")

    @route('/deliverymatch/callback/<string:delivery_order_number>', auth='api_key', website=True, type='json', methods=['POST'])
    def handler(self, delivery_order_number):
        data = request.httprequest.data
        self._logger.info(f"incoming REQUEST OUTBOUND {data}")
        req = yaml.load(data, Loader=yaml.SafeLoader)
        stock_picking = request.env["stock.picking"].search([("delivery_order_number", "=", delivery_order_number)])

        if not stock_picking:
            raise NotFound("No such sale")

        if ('status' not in req) or ('packages' not in req):
            raise BadRequest("Incorrect payload")


        tracking_urls = []
        for index, package in enumerate(req["packages"]):
            tracking_url = package["trackingURL"]
            barcode = package["barcode"]

            tracking_urls.append(f'<a href="{tracking_url}">Tracking {barcode}</a>')
            stock_picking.write({"packages": [(0, 0, {
                "weight": package["weight"],
                "length": package["length"],
                "height": package["height"],
                "width": package["width"],
                "type": package["type"],
                "description": package["description"],
            })]})

        stock_move = request.env["stock.move"].search([("picking_id", "=", stock_picking.id)])

        if not stock_move: raise NotFound("No stock move not found.")

        for line in stock_move:
            if not 'quantity_done' in line: continue
            line.write({"quantity_done": line.product_uom_qty})

        has_labels = "labelURL" in req

        if not stock_picking._check_backorder() and has_labels:
            stock_picking.button_validate()

        stock_picking.dm_status = req['status']

        if has_labels:
            stock_picking.shipment_label_attachment = helper.Helper().convert_label(req["labelURL"])

        if len(tracking_urls) > 0:
            stock_picking.tracking_urls = "<br>".join(tracking_urls)

        return {"status": "success"}

    @route('/deliverymatch/callback/inbound/<string:delivery_order_number>', auth='api_key', website=True, type='json', methods=['POST'])
    def handleInbound(self, delivery_order_number):
        data = request.httprequest.data
        self._logger.info(f"incoming REQUEST INBOUND {data}")
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

            if not "quantity" in stock_move: continue

            stock_move.write({"quantity": item['quantity']})


        return {"status": "success"}
