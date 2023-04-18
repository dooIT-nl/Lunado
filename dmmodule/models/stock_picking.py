# stock.picking
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import requests, json, traceback, logging, base64
from .stock_picking_handler import StockPickingHandler
from .helper import Helper



class StockPicking(models.Model):
    _inherit = "stock.picking"
    
    dm_carrier_name = fields.Char(string="Carrier Name")
    dm_service_level_name = fields.Char(string="Service Level Name")
    dm_service_level_description = fields.Char(string="Service Level Description")
    dm_delivery_date = fields.Char(string="Delivery Date")
    dm_pickup_date = fields.Char(string="Pickup Date")
    dm_buy_price = fields.Float(string="Buy Price")
    dm_sell_price = fields.Float(string="Sell Price")
    dm_shipment_id = fields.Char(string="DM Shipment ID", default=None)
    dm_method_id = fields.Char(string="Method ID")
    dm_check_id = fields.Char(string="Check ID")  
    shipment_label_attachment = fields.Binary(string="Shipment label(s)")
    shipment_tracking_url = fields.Char(string="Tracking Link")
    
    dm_shipment_url = fields.Char(string="Open Shipment in DeliveryMatch")
    delivery_option_selected = fields.Boolean(default=False)
    show_hub_btn = fields.Boolean(default=False)
    
    
    
    @api.model
    def create(self, vals):
        res = super(StockPicking, self).create(vals)
        res.show_hub_btn = res.is_external_warehouse()
        res.set_delivery_option(True)
        return res

    def write(self, vals):
        res = super().write(vals)
        if 'partner_id' in vals:
            self.set_delivery_option(True)
        return res


    @api.onchange('location_id')
    def toggle_hub_button(self):
        try:
            self.show_hub_btn = self.is_external_warehouse()


        except ValueError as e:
            self._origin.warning_popup("Error", "something went wrong...")

        
    
    def get_api_key(self):
        return self.env['ir.config_parameter'].sudo().get_param('dmmodule.api_key', default=None)


    def get_client_id(self):
        return self.env['ir.config_parameter'].sudo().get_param('dmmodule.client_id', default=None)


    def get_base_url(self):
        return self.env['ir.config_parameter'].sudo().get_param('dmmodule.base_url', default=None)


    def get_delivery_option_preference(self):
        return self.env['ir.config_parameter'].sudo().get_param('dmmodule.delivery_option_preference', default="lowest")
 
    
    def get_warehouse(self):
        warehouse = self.env['stock.warehouse'].search([('lot_stock_id','=',self.location_id.id)])
        return warehouse
    
    def override_product_length(self):
        return self.env['ir.config_parameter'].sudo().get_param('dmmodule.override_length', default=False)
    

    def get_dm_warehouse_id(self):
        warehouse = self.get_warehouse()
        return warehouse.warehouse_options
        # returns DeliveryMatch warehouse id 

        
    def is_external_warehouse(self):
        warehouse = self.get_warehouse()
        return warehouse.dm_external_warehouse

    
    def show_popup(self, message):
        view_id = self._origin.env.ref('dmmodule.view_popup_wizard_form').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'DeliveryMatch - Warning',
            'view_mode': 'form',
            'res_model': 'popup_wizard',
            'views': [(view_id, 'form')],
            'target': 'new',
            'context': {
                'default_message': message,
            }
        }

    def warning_popup(self, title, message):
        return {
            'warning': {
                'title': title,
                'message': message
            }
        }


    @api.onchange('location_id', 'move_ids_without_package', 'company_id', 'sale_id')
    def set_delivery_option(self, is_onchange=False):
        try:
            print("start")
            if(self.get_delivery_option_preference() != "nothing" and self._origin.id != False):
                delivery_id = self._origin.id
                sale_order_id = self._origin.sale_id.id
                operation_lines = self._origin.move_ids_without_package
                customer= self._origin.partner_id

                DmHandle = StockPickingHandler(self.get_base_url(), self.get_api_key(), self.get_client_id(), self.override_product_length(), odoo_env=self, shipping_preference=self.get_delivery_option_preference())
                
                dm_shipping_response = DmHandle.get_shipping_options_delivery_level(sale_order_id=sale_order_id, operation_lines=operation_lines, sale_order=self.sale_id, delivery_id=delivery_id, customer=customer, dm_shipment_id=self.dm_shipment_id)
                
                if dm_shipping_response != True:
                    if is_onchange == False:

                        return self.warning_popup("DeliveryMatch - Warning", dm_shipping_response)
                    else:
                        self._origin.message_post(body=dm_shipping_response, subject=_("DeliveryMatch - Warning"), message_type="notification")

                else:
                    self._origin.message_post(body=f"Selected {self._origin.get_delivery_option_preference()} delivery option!", subject=_("DeliveryMatch - Auto selection"))
        
        except ValueError as e:
            self.warning_popup("DeliveryMatch - Error", "Something went wrong while auto-selecting a shipping option.")

    
    
    def show_delivery_options(self):
        stock_picking_handler = StockPickingHandler(self.get_base_url(), self.get_api_key(), self.get_client_id(), self.override_product_length(), odoo_env=self)
        delivery_id = self._origin.id
        sale_order_id = self._origin.sale_id.id
        operation_lines = self._origin.move_ids_without_package
        customer= self._origin.partner_id
        shipping_options_response =  stock_picking_handler.get_shipping_options_delivery_level(sale_order_id=sale_order_id, operation_lines=operation_lines, sale_order=self.sale_id, delivery_id=delivery_id, customer=customer, dm_shipment_id=self.dm_shipment_id)
        
        if shipping_options_response != True:
            return self.show_popup(shipping_options_response)


        view_id = self.env.ref('dmmodule.delivery_options_tree_delivery_level').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Shipping options',
            'res_model': 'dm.deliver.options',
            'view_type': 'tree',
            'view_mode': 'tree',
            "view_id": view_id,
            "domain": [("odooOrderId", "=", self.id)],
            'target': 'new'
        }    
    


    def book_delivery(self):

        stock_picking_handler = StockPickingHandler(self.get_base_url(), self.get_api_key(), self.get_client_id(), self.override_product_length(), odoo_env=self)
        delivery_id = self._origin.id
        sale_order_id = self._origin.sale_id.id
        dm_order_number = f'{sale_order_id}-{delivery_id}'

        operation_lines = self._origin.move_ids_without_package
        customer= self._origin.partner_id
        
        booking_response = stock_picking_handler.book_delivery_order(operation_lines, self.sale_id, dm_order_number, customer, self.dm_shipment_id)
        
        if booking_response != True:
            return self.show_popup(booking_response)


        self.message_post(body=f"Order booked to carrier in DeliveryMatch on: {Helper().get_time_stamp()}")
        return
    
    def set_delivery_to_hub(self):
        stock_picking_handler = StockPickingHandler(self.get_base_url(), self.get_api_key(), self.get_client_id(), self.override_product_length() ,odoo_env=self)
        delivery_id = self._origin.id
        sale_order_id = self._origin.sale_id.id
        dm_order_number = f'{sale_order_id}-{delivery_id}'

        operation_lines = self._origin.move_ids_without_package
        customer= self._origin.partner_id
        
        booking_response = stock_picking_handler.book_delivery_order(operation_lines, self.sale_id, dm_order_number, customer, self.dm_shipment_id, True)
        
        if booking_response != True:
            return self.show_popup(booking_response)


        self.message_post(body=f"Order booked to warehouse in DeliveryMatch on: {Helper().get_time_stamp()}")
        return


    