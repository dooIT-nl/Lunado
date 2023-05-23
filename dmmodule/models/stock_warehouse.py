# stock.picking
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import traceback
import logging


class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"
    dm_external_warehouse = fields.Boolean(default=False, string="External Warehouse - DeliveryMatch")
    WAREHOUSE_CODES = []
    for i in range(1, 31): WAREHOUSE_CODES.append((str(i), str(i)))
        
    warehouse_options = fields.Selection(selection=WAREHOUSE_CODES, string='Warehouse nr DeliveryMatch', default="1", required=True)


    def set_as_external_warehouse(self):
        warehouses = []
        for warehouse in self:
            external_warehouse = warehouse.dm_external_warehouse 
            
            if external_warehouse == True:
                warehouse.dm_external_warehouse = False
            else:
                warehouses.append(warehouse.name)
                warehouse.dm_external_warehouse = True

        
        succes_message = "Selected Warehouses Updated!"
        
        if warehouses:
            has_have = "has"
            if len(warehouses) > 1: 
                has_have = "have"                
                
            warehouses = ", ".join(warehouses)
            succes_message = f"{warehouses} {has_have} been set as external warehouses for DeliveryMatch"
            
        self.update_sale_orders()

        view_id = self.env.ref('dmmodule.view_popup_wizard_form').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Warehouses Changes Saved!',
            'view_mode': 'form',
            'res_model': 'popup_wizard',
            'views': [(view_id, 'form')],
            'target': 'new',
            'context': {
                'default_message': succes_message,
            }
        }
        

        
    def update_sale_orders(self):
        show_hub_btn = self.env['ir.config_parameter'].sudo().get_param('dmmodule.sale_order_to_hub', default=False)
        
        if show_hub_btn == "True":
            sale_orders = self.env['sale.order'].search([])
            for sale_order in sale_orders:
                show_external_warehouse = sale_order.warehouse_id.dm_external_warehouse
                sale_order.write({'show_hub_btn': show_external_warehouse})
        
