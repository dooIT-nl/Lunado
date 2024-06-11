import logging
from odoo import http
from odoo.http import request, Controller
import json

class Deliverymatch(Controller):

    @http.route('/deliverymatch/odoo', auth='public', type='json', website=True, method=['POST'])
    def handle_post_request(self, **post_data):
        data = json.loads(request.httprequest.data)
        headers = request.httprequest.headers
        api_key = headers.get('access_token', "empty")
        
        if(api_key != "test123"): return {'status': 'failed', 'message': 'Invalid credentials'}
        
        sale_order = request.env['sale.order'].sudo().search([('id', '=', '38')], limit=1)
        sale_order.client_order_ref = data.get('customer_ref', None)
            
            
        return {'status': 'success', 'message': 'Request handled successfully'}

