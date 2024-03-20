from .deliverymatch_exception import DeliveryMatchException
import logging, traceback
from .shipment_type import ShipmentType
from .helper import Helper

_logger = logging.getLogger("DeliveryMatch - Shipment")

class Shipment:

    def __init__(
            self,
            odoo_order_display_name,
            incoterm,
            type: ShipmentType,
            odoo_order_id=None,
            id=None,
            status="new",
            reference=None,
            language="EN",
            currency="EUR",
            inbound=False,
            note="",
            to_hub=False,
            delivery_date="",
            is_external_warehouse: bool = False,
            odoo_sale_order_id: str = None
    ):
        try:
            self.odoo_order_display_name = odoo_order_display_name
            self.incoterm = incoterm
            self.type = type
            self.odoo_order_id = odoo_order_id
            self.id = id
            self.status = status
            self.reference = reference
            self.language = language
            self.currency = currency
            self.inbound = inbound
            self.note = note
            self.to_hub = to_hub
            self.delivery_date = delivery_date
            self.is_external_warehouse = is_external_warehouse
            self.odoo_sale_order_id = odoo_sale_order_id

            for attribute, value in vars().items():
                if attribute in ["odoo_order_number"] and not value:
                    raise DeliveryMatchException("Could not fetch shipment Odoo order number. Please try again.")
                
                # TODO check if this is the right way to do it
                if inbound is True:
                    self.incoterm = ""

        except DeliveryMatchException as e:
            _logger.error(e)
            raise DeliveryMatchException(e)
        
        except Exception as e:
            _logger.error(e)
            _logger.error(traceback.format_exc())
            raise Exception("Something went wrong fetching the shipment data. Please check your data and try again.")

    def __repr__(self):  
        return f"odoo_order_display_name={self.odoo_order_display_name} incoterm={self.incoterm}, odoo_order_id={self.odoo_order_id}, id={self.id}, status={self.status}, reference={self.reference}, language={self.language}, currency={self.currency}, inbound={self.inbound}, note={self.note}, to_hub={self.to_hub}, delivery_date={self.delivery_date}"

    def format_shipment_reference(self):
        if Helper.is_empty(self.reference) is not True:
            self.reference = self.reference.replace(" ", "_")