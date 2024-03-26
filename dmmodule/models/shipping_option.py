class ShippingOption:
    def __init__(self, shipment_id, method_id, check_id, carrier_name, service_level_name, service_level_description, delivery_date, date_pickup, buy_price, sell_price, carrier_id=None, service_level_id=None):
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
        self.carrier_id = carrier_id
        self.service_level_id = service_level_id


class ShippingOptions:
    def __init__(self):
        self.shipping_options = []

    def add_shipping_option(self, shipping_option):
        self.shipping_options.append(shipping_option)

    def get_shipping_options(self):
        return self.shipping_options