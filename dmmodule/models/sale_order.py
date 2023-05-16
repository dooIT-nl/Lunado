from odoo import api, fields, models, _ , exceptions
from odoo.exceptions import UserError
import requests, traceback, logging
from .sale_order_handler import SaleOrderHandler
from .deliverymatch_exception import DeliveryMatchException
import datetime

class SaleOrder(models.Model):
    name="dm.sale.order"
    _logger = logging.getLogger("DeliveryMatch - SaleOrder")
    _inherit = "sale.order"
    dm_shipment_url = "https://engine-test.deliverymatch.eu/shipment/view/"

    dm_carrierName = fields.Char(string="Carrier Name")
    dm_serviceLevelName = fields.Char(string="Service Level Name")
    dm_serviceLevelDescription = fields.Char(string="Service Level Description")
    dm_deliveryDate = fields.Char(string="Delivery Date")
    dm_pickup_date = fields.Char(string="Pickup Date")
    dm_buyPrice = fields.Float(string="Buy Price")
    dm_price = fields.Float(string="Sell Price")
    dm_shipment_id = fields.Char(string="DM Shipment ID", default=None)
    dm_methodId = fields.Char(string="Method ID")
    dm_checkId = fields.Char(string="Check ID")
    dm_shipment_booked = fields.Boolean(default=False)    
    shipmentURL = fields.Char()
    delivery_option_selected = fields.Boolean(default=False)
    order_booked = fields.Boolean(default=False)
    shipment_label_attachment = fields.Binary(string="Shipment label(s)")
    shipment_label = fields.Char()
    shipment_tracking_url = fields.Char()
    show_hub_btn = fields.Boolean(default=False)
    total_shipment_price = fields.Float(string='Total including Shipping costs', compute='_compute_custom_amount')

    
    @api.depends('amount_total', 'amount_untaxed')
    def _compute_custom_amount(self):
        for record in self:
            record.total_shipment_price = record.amount_total + self.dm_price    
    
    def get_api_key(self):
        return self.env['ir.config_parameter'].sudo().get_param('dmmodule.api_key', default=None)
    

    def get_client_id(self):
        return self.env['ir.config_parameter'].sudo().get_param('dmmodule.client_id', default=None)
    
    
    def get_base_url(self):
        return self.env['ir.config_parameter'].sudo().get_param('dmmodule.base_url', default=None)


    def get_delivery_option_preference(self):
        return self.env['ir.config_parameter'].sudo().get_param('dmmodule.delivery_option_preference', default=False)
    
    
    def override_product_length(self):
        return self.env['ir.config_parameter'].sudo().get_param('dmmodule.override_length', default=False)


    def warning_popup(self, title, message):
        return {
            'warning': {
                'title': title,
                'message': message
            }
        }

    @api.model
    def create(self, vals):
        res = super(SaleOrder, self).create(vals)
        res.set_delivery_option()
        return res



    @api.onchange('partner_id', 'order_line', 'incoterm', 'company_id')
    def set_delivery_option(self):
        try:
            self._logger.info("Auto select shipping option in SaleOrder")
            if (self._origin.id != False and self.get_delivery_option_preference() != "nothing"):
                DmHandle = SaleOrderHandler(self, self.get_base_url(), self.get_api_key(), self.get_client_id(), self.override_product_length())
                
                dm_delivery_option =  DmHandle.get_delivery_options(self._origin.id, self._origin.partner_id, self._origin.order_line, self._origin.incoterm.code,
                                                                    self._origin.warehouse_id, preference=self._origin.get_delivery_option_preference())
                
                if dm_delivery_option != True:
                    self._logger.error(f"An error occurred in set_delivery_option {dm_delivery_option}")
                    return self.warning_popup("DeliveryMatch - Warning", dm_delivery_option)
                
                self._origin.message_post(body=f"DeliveryMatch → auto selected {self._origin.get_delivery_option_preference()} delivery option!")
                
                    
        except ValueError as e:
            self._logger.error(f"An error occurred in set_delivery_option {e}")
            return self.warning_popup("DeliveryMatch - Warning", e)




    def show_delivery_options(self):
        try:
            self.message_post(body="Requesting shipping options from DeliveryMatch...")
            self._logger.info(f"{self.show_delivery_options.__name__}: getting base_url, api_key, client_id and override product length")
            DmHandle = SaleOrderHandler(self, self.get_base_url(), self.get_api_key(), self.get_client_id(),self.override_product_length())
            
            
            DmHandle.get_delivery_options(self.id, self.partner_id, self.order_line, self.incoterm.code, self.warehouse_id, manual=True)

            view_id = self.env.ref('dmmodule.delivery_options_tree').id
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
        except DeliveryMatchException as e:
            return self.show_popup(str(e))

        except ValueError as e:
            error_message = traceback.format_exc()
            self._logger.error(error_message)
            raise UserError(e)
        
    def book_order(self):
        try:
            self._logger.info("Booking Sales Order...")
            if not self.delivery_option_selected:
                raise Exception("Choosing a shipping option is mandatory before booking an order.")

            sale_order_handler = SaleOrderHandler(odoo_env=self,base_url=self.get_base_url(), api_key=self.get_api_key(), client_id=self.get_client_id(), override_product_length=self.override_product_length())
            customer = self.partner_id
            
            sale_order_handler.book_order_dm(
                order_number=self.id,
                incoterm=self.incoterm.code,
                customer_ref=self.client_order_ref,
                customer_note=customer.comment,
                customer_name=customer.name,
                company_name=customer.company_name,
                address1=customer.street,
                address2=customer.street2,
                street=customer.street,
                country=customer.country_code,
                city=customer.city,
                zipcode=customer.zip,
                customer_id=customer.id,
                customer_email=customer.email,
                customer_phone=customer.phone,
                order_line=self.order_line,
                price_inc=self.amount_total,
                pric_exc=self.amount_untaxed
            )

            time_stamp = self.get_time_stamp()
            self.message_post(body=f"Order booked to carrier in DeliveryMatch on: {time_stamp}")
            
        except Exception as e:
            raise UserError(e)
        
    def set_status_hub(self):
        try:
            sale_order_handler = SaleOrderHandler(self, self.get_base_url() ,self.get_api_key(), self.get_client_id(), self.override_product_length())
            status_to_hub =  sale_order_handler.send_order_to_hub()
            
            if status_to_hub != True:
                return self.show_popup(status_to_hub)
            
            time_stamp = self.get_time_stamp()
            self.message_post(body=f"Order booked to warehouse in DeliveryMatch on: {time_stamp}")
            
            
        except ValueError as e:
            raise UserError(e)
    
    
    def get_time_stamp(self) -> str:
        current_time = datetime.datetime.now()
        # Format the current time as yy-mm-dd h:m:s
        formatted_time = current_time.strftime("%y-%m-%d %H:%M:%S")
        return formatted_time

    
    @api.onchange('warehouse_id')
    def toggle_hub_button(self):
        try:
            sale_order_to_hub = self._origin.env['ir.config_parameter'].sudo().get_param('dmmodule.sale_order_to_hub', default=False)
            
            if sale_order_to_hub == "True":
                self.write({'show_hub_btn': self.warehouse_id.dm_external_warehouse})
            else:
                self.write({'show_hub_btn': False})


        except ValueError as e:
            self._origin.warning_popup("Error", "something went wrong...")


    def show_popup(self, message):
        view_id = self.env.ref('dmmodule.view_popup_wizard_form').id
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


            

