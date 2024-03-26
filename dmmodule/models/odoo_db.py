import logging, traceback
from .shipping_option import *


class OdooDb:
    def __init__(self, odoo_env):
        self.odoo_env = odoo_env
        self._logger = logging.getLogger("DeliveryMatch - OdooDb")

    # deliverOptions dict: carrierName, serviceLevelName, serviceLevelDescription, deliveryDate, buyPrice, price, shipmentId, odooOrderId
    def insert_into_deliver_options(
        self, shipping_options, odoo_order_id
    ):
        try:
            self._logger.info(
                "inserting shipping options from DM to Odoo dm.deliver.options table"
            )
            for so in shipping_options:
                self.odoo_env.env["dm.deliver.options"].create(
                    {
                        "carrierName": so.carrier_name,
                        "serviceLevelName": so.service_level_name,
                        "serviceLevelDescription": so.service_level_description,
                        "deliveryDate": so.delivery_date,
                        "dm_pickup_date": so.date_pickup,
                        "buyPrice": so.buy_price,
                        "price": so.sell_price,
                        "shipmentId": so.shipment_id,
                        "odooOrderId": odoo_order_id,
                        "methodId": so.method_id,
                        "checkId": so.check_id,
                        "carrier_id": so.carrier_id,
                        "service_level_id": so.service_level_id
                    }
                )
            self._logger.info("Insertion process finished successfully")
        except Exception as e:
            self._logger.error(
                f"An error occurred while inserting shipping options in Odoo: {e}"
            )
            raise Exception("An error occurred while fetching the shipping options")

    def has_odoo_order_id(self, id: int):
        try:
            self._logger.info("Checking if odoo_id is in dm.deliver.options")
            foundIds = self.odoo_env.env["dm.deliver.options"].search(
                [("odooOrderId", "=", id)]
            )

            if not foundIds:
                self._logger.info("odoo_id not found in dm_deliver.options")
                return False
            else:
                self._logger.info("odoo_id found in dm_deliver.options")

                return True
        except Exception as e:
            self._logger.error(
                f"An error occurred while checking if odoo_id is in dm.deliver.options: {e}"
            )
            raise Exception("There was an error encountered during the process")

    # def getCountryFromDB(self, country_id, state_id):
    #     print(country_id)
    #     print(state_id)
    #     state = self.env['res.country.state'].search([('country_id', '=', country_id)])
    #     return state

    def delete_delivery_option(self, id: int):
        try:
            self._logger.info("Deleting shipping option from dm.deliver.options")
            if self.has_odoo_order_id(id):
                self.odoo_env.env["dm.deliver.options"].search(
                    [("odooOrderId", "=", id)]
                ).unlink()

            self._logger.info("Shipping option deleted")
        except Exception as e:
            self._logger.error(
                f"An error occurred while deleting shipping options from dm.deliver.options: {e}"
            )
            raise Exception(
                "Failed to remove a shipping option from the shipping options table"
            )
