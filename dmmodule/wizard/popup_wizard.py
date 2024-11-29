from odoo import fields, models

class PopupWizard(models.TransientModel):
    _name = 'popup_wizard'
    _description = 'Popup Wizard'

    message = fields.Char('Message', required=True)

    def close_popup(self):
        return {'type': 'ir.actions.act_window_close'}