# -*- coding: utf-8 -*-
from odoo import http


class Deliverymatch(http.Controller):

    @http.route('/test/deliverymatch/', auth='public', method=['GET'])
    def index(self):
        return "Hello, world"

    # @http.route('/deliverymatch/deliverymatch/objects', auth='public')
    # def list(self, **kw):
    #     return http.request.render('deliverymatch.listing', {
    #         'root': '/deliverymatch/deliverymatch',
    #         'objects': http.request.env['deliverymatch.deliverymatch'].search([]),
    #     })
    #
    # @http.route('/deliverymatch/deliverymatch/objects/<model("deliverymatch.deliverymatch"):obj>', auth='public')
    # def object(self, obj, **kw):
    #     return http.request.render('deliverymatch.object', {
    #         'object': obj
    #     })
