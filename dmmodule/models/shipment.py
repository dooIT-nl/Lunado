from .deliverymatch_exception import DeliveryMatchException
import logging, traceback

_logger = logging.getLogger("DeliveryMatch - Shipment")

class Shipment:


    def __init__(self, odoo_order_display_name, incoterm, odoo_order_id=None, id=None, status="new", reference=None, language="EN", currency="EUR", inbound=False, note=None):
        try:
            self.odoo_order_display_name = odoo_order_display_name
            self.incoterm = incoterm
            self.odoo_order_id = odoo_order_id
            self.id = id
            self.status = status
            self.reference = reference
            self.language = language
            self.currency = currency
            self.inbound = inbound
            self.note = note

            for attribute, value in vars().items():
                if attribute in ["odoo_order_number"] and not value:
                    raise DeliveryMatchException("Could not fetch shipment Odoo order number. Please try again.")

                if(inbound == False):
                    if attribute in ["incoterm"] and not value:
                        raise DeliveryMatchException("Please select an incoterm.")
                
                # TODO check if this is the right way to do it
                if(inbound == True):
                    self.incoterm = ""

        except DeliveryMatchException as e:
            _logger.error(e)
            raise DeliveryMatchException(e)
        
        except Exception as e:
            _logger.error(e)
            _logger.error(traceback.format_exc())
            raise Exception("Something went wrong fetching the shipment data. Please check your data and try again.")


