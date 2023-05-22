class ShippingOption:
    def __init__(self, shipment_id, method_id, check_id, carrier_name, service_level_name, service_level_description, delivery_date, date_pickup, buy_price, sell_price):
        self.shipment_id = shipment_id
        self.method_id = method_id
        self.check_id = check_id
        self.carrier_name = carrier_name
        self.service_level_name = service_level_name
        self.service_level_description = service_level_description
        self.delivery_date = delivery_date
        self.date_pickup = date_pickup
        self.buy_price = buy_price
        self.sell_price = sell_price


class ShippingOptions:
    def __init__(self):
        self.shipping_options = []

    def add_shipping_option(self, shipping_option):
        self.shipping_options.append(shipping_option)

    def get_shipping_options(self) -> list[ShippingOption]:
        return self.shipping_options










    # def format_delivery_options(self, data):
    #     try:
    #         self._logger.info("Formating shipping options from DM...")
    #         data = json.loads(data)

    #         deliverOptions = []
    #         shipmentId = data["shipmentID"]
    #         shipmentMethods: dict = data["shipmentMethods"]["all"]

    #         for key in shipmentMethods:
    #             shipmentMethod: dict = shipmentMethods.get(key)

    #             for method in shipmentMethod:
    #                 methodId = method.get("methodID")
    #                 checkId = method.get("checkID")
    #                 carrierName = method.get("carrier").get("name")
    #                 serviceLevelName = method.get("serviceLevel").get("name")
    #                 serviceLevelDescription = method.get("serviceLevel").get("description")
    #                 deliveryDate = method.get("dateDelivery")
    #                 datePickup = method.get("datePickup")

    #                 buyPrice = method.get("buy_price")
    #                 price = method.get("price")

    #                 deliverOption = {
    #                     "carrierName": carrierName,
    #                     "serviceLevelName": serviceLevelName,
    #                     "serviceLevelDescription": serviceLevelDescription,
    #                     "deliveryDate": deliveryDate,
    #                     "datePickup": datePickup,
    #                     "buyPrice": buyPrice,
    #                     "price": price,
    #                     "shipmentId": shipmentId,
    #                     "odooOrderId": self.odoo_env.id,
    #                     "methodId": methodId,
    #                     "checkId": checkId,
    #                 }

    #                 deliverOptions.append(deliverOption)

    #         return deliverOptions
    #     except Exception as e:
    #         tb = traceback.format_exc()
    #         self._logger.error(f"{e} \n{tb}")
    #         raise Exception("Failed to update the shipping options.")