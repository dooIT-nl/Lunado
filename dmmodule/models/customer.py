from .deliverymatch_exception import DeliveryMatchException
from odoo.tools import html2plaintext

class Customer:
    
    def __init__(self,id, name, company_name, address1, address2, street, postcode, city, country, phone_number, email, note="", is_company=False, is_franco=False):
        self.id = id
        self.name = name
        self.company_name = company_name
        self.address1 = address1
        self.address2 = address2
        self.street = street
        self.postcode = postcode
        self.city = city
        self.country = country
        self.phone_number = phone_number
        self.email = email
        self.note = html2plaintext(note)
        self.is_franco = is_franco
        
        for attribute, value in vars().items():
            if(attribute == "company_name" and is_company == True):
                    self.company_name = self.name
            
            if not value and attribute not in ["address2", "is_company", "note", "company_name", "is_franco"]:
                
                    # raise DeliveryMatchException(f"Please ensure that the customer name and company name are provided")

                    
                raise DeliveryMatchException(f"Please make sure to provide a value for the customer '{attribute}'.")
    

            
        


