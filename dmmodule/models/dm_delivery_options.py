from odoo import fields, models
from odoo.exceptions import UserError

import requests, json
from .dm_api import DmApi
from .helper import Helper


class DmDeliveryOptions(models.Model):
    _name = "dm.deliver.options"
    _description = "Deliver Options"
    carrierName = fields.Char(string="Carrier Name")
    serviceLevelName = fields.Char(string="Service Name")
    serviceLevelDescription = fields.Char(string="Service Description")
    deliveryDate = fields.Char(string="Delivery Date")
    dm_pickup_date = fields.Char(string="Pickup Date")
    buyPrice = fields.Char(string="Buy Price")
    price = fields.Float(string="Price")
    shipmentId = fields.Integer(string="DM Shipment ID")
    odooOrderId = fields.Integer(string="Odoo Order ID")
    methodId = fields.Char(string="Method ID")
    checkId = fields.Char(string="Check ID")
    carrier_id = fields.Integer(string="Carrier ID")
    service_level_id = fields.Integer(string="Service Level ID")

    def config_attribute(self, attribute, default=None):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(f"dmmodule.{attribute}", default=default)
        )

    def remove_delivery_options(self, odoo_order_id):
        self.env["dm.deliver.options"].search([('odooOrderId','=',odoo_order_id)]).unlink()      


    def set_shipping_option_delivery_level(self):
        selected_delivery_option = self[0]
        odoo_order_id = selected_delivery_option.odooOrderId

        if len(self) > 1:   
            self.remove_delivery_options(odoo_order_id)
            raise UserError("We're sorry, but you can only select one shipping option at a time. Please deselect any additional options and try again.")
        elif len(self) < 1:
            self.remove_delivery_options(odoo_order_id)
            raise UserError ("Please select at least one shipping option to proceed")

        # Selects the sale order by ID
        delivery_order =  self.env['stock.picking'].search([('id', '=', odoo_order_id)])
        
        # Update the found delivery order
        delivery_order.dm_carrier_name = selected_delivery_option.carrierName
        delivery_order.dm_service_level_name = selected_delivery_option.serviceLevelName
        delivery_order.dm_service_level_description = selected_delivery_option.serviceLevelDescription
        delivery_order.dm_delivery_date = selected_delivery_option.deliveryDate
        delivery_order.dm_pickup_date = selected_delivery_option.dm_pickup_date
        delivery_order.dm_buy_price = selected_delivery_option.buyPrice
        delivery_order.dm_sell_price = selected_delivery_option.price
        delivery_order.dm_shipment_id = selected_delivery_option.shipmentId
        delivery_order.dm_method_id = selected_delivery_option.methodId
        delivery_order.dm_check_id = selected_delivery_option.checkId
        delivery_order.delivery_option_selected = True

        # POST shipmentmethod to deliverymatch
        base_url = delivery_order.get_base_url()
        api_key = delivery_order.get_api_key()
        client_id = delivery_order.get_client_id()

        dm_api = DmApi(base_url, api_key, client_id)
        dm_api.updateShipmentMethod(selected_delivery_option.shipmentId, odoo_order_id, selected_delivery_option.methodId, selected_delivery_option.deliveryDate)

        # remove NOT SELECTED delivery options
        self.remove_delivery_options(odoo_order_id)

        if self.config_attribute('determine_delivery_date', False):
            dm_api.save_pickup_date(delivery_order.dm_shipment_id, Helper.remove_time_from_datetime(delivery_order.scheduled_date))

        return

    # SET SHIPPING OPTION ON SALES ORDER
    def setSelectedDeliveryOption(self):
        selected_delivery_option = self[0]
        odooOrderId = selected_delivery_option.odooOrderId

        if len(self) > 1:   
            self.remove_delivery_options(odooOrderId)
            raise UserError("We're sorry, but you can only select one shipping option at a time. Please deselect any additional options and try again.")
        elif len(self) < 1:
            self.remove_delivery_options(odooOrderId)
            raise UserError ("Please select at least one shipping option to proceed")

        
        
        # Selects the sale order by ID
        update_sale_order =  self.env['sale.order'].search([('id', '=', odooOrderId)])
        
        # Update the found sale order
        update_sale_order.dm_carrierName = selected_delivery_option.carrierName
        update_sale_order.dm_serviceLevelName = selected_delivery_option.serviceLevelName
        update_sale_order.dm_serviceLevelDescription = selected_delivery_option.serviceLevelDescription
        update_sale_order.dm_deliveryDate = selected_delivery_option.deliveryDate
        update_sale_order.dm_pickup_date = selected_delivery_option.dm_pickup_date
        update_sale_order.dm_buyPrice = selected_delivery_option.buyPrice
        update_sale_order.dm_price = selected_delivery_option.price
        update_sale_order.dm_shipment_id = selected_delivery_option.shipmentId
        update_sale_order.dm_methodId = selected_delivery_option.methodId
        update_sale_order.dm_checkId = selected_delivery_option.checkId
        update_sale_order.delivery_option_selected = True
        update_sale_order.carrier_id = selected_delivery_option.carrier_id
        update_sale_order.service_level_id = selected_delivery_option.service_level_id


        # POST shipmentmethod to deliverymatch
        base_url = update_sale_order.get_base_url()
        api_key = update_sale_order.get_api_key()
        client_id = update_sale_order.get_client_id()

        dm_api = DmApi(base_url, api_key, client_id)
        dm_api.updateShipmentMethod(selected_delivery_option.shipmentId, odooOrderId, selected_delivery_option.methodId, selected_delivery_option.deliveryDate)

        # remove NOT SELECTED delivery options
        self.remove_delivery_options(odooOrderId)
        self.set_shipping_cost(order_id=odooOrderId, sell_price=update_sale_order.dm_price, carrier_name=update_sale_order.dm_carrierName)
        return
    
    
    def set_shipping_cost(self, order_id, sell_price, carrier_name):
        dm_shipping_cost = self.env['product.product'].search([('default_code', '=', 'DeliveryMatch')], limit=1)
        order = self.env['sale.order'].browse(order_id)
    
        order_line_shipping_cost = self.env["sale.order.line"].search([('order_id','=', order.id), ('product_id','=', dm_shipping_cost.id)])
        
        if(order_line_shipping_cost):
            order_line_shipping_cost.price_unit = sell_price
            order_line_shipping_cost.name = carrier_name
            return
                
                
        
        order.order_line.create({
            'product_id': dm_shipping_cost.id,
            'order_id': order.id,
            'product_uom_qty': 1,
            'price_unit': sell_price,
            'name': carrier_name,
        })