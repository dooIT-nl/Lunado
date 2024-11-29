from odoo import models


class ResPartner(models.Model):
    _inherit = "res.partner"

    def as_deliverymatch_customer(self):
        return {
                "id": self.id,
                "address": {
                    "name": self.name,
                    "companyName": self.company_name if self.company_name else None,
                    "address1": self.street,
                    "address2": self.street2 if self.street2 else None,
                    "street": self.street,
                    "postcode": self.zip,
                    "city": self.city,
                    "country": self.country_code,
                },
                "contact": {
                    "phoneNumber": self.phone,
                    "email": self.email,
                },
            }