import json

import odoo
import yaml
from odoo.http import route, request, NotFound
from werkzeug.exceptions import BadRequest


class Callback(odoo.http.Controller):
    @route('/deliverymatch/callback/<int:delivery_order_number>', auth='api_key', website=True, type='json', methods=['POST'])
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

            stock_picking.action_set_quantities_to_reservation()
            if not stock_picking._check_backorder():
                stock_picking.button_validate()

        stock_picking.dm_status = req['status']

        return {"status": "success"}