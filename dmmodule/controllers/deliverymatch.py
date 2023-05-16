import logging
from odoo import http


class deliverymatch(http.Controller):

    @http.route('/test/dm', auth='public')
    def index(self):
        return "Hello, world"
