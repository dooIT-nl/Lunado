import json

import odoo
import yaml
from odoo.http import route, request, NotFound
from werkzeug.exceptions import BadRequest


class Callback(odoo.http.Controller):
    @route('/deliverymatch/callback/<int:sale_id>', auth='api_key', website=True, type='json', methods=['POST'])
    def handler(self, sale_id):
        data = request.httprequest.data
        req = yaml.load(data, Loader=None)

        stock_picking = request.env["stock.picking"].search([("id", "=", sale_id)])

        if not stock_picking:
            raise NotFound("No such sale")

        if ('status' not in req) or ('labels' not in req):
            raise BadRequest("Incorrect payload")

        if len(stock_picking.labels) == 0:
            for index, label in enumerate(req["labels"]):
                try:
                    stock_picking.write({"labels": [(0, 0, {
                        "label_url": label["labelURL"],
                        "barcode": label["barcode"],
                        "tracking_url": label["trackingURL"] if "trackingURL" in label else "",
                        "weight": stock_picking.packages[index].weight,
                        "length": stock_picking.packages[index].length,
                        "height": stock_picking.packages[index].height,
                        "width": stock_picking.packages[index].width,
                        "type": stock_picking.packages[index].type,
                        "description": stock_picking.packages[index].description,
                    })]})
                except IndexError:
                    stock_picking.write({"labels": [(0, 0, {
                        "label_url": label["labelURL"],
                        "barcode": label["barcode"],
                        "tracking_url": label["trackingURL"] if "trackingURL" in label else "",
                    })]})

        stock_picking.dm_status = req['status']

        return {"status": "success"}