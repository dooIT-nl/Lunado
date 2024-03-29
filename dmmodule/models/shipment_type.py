from enum import Enum
class ShipmentType(Enum):
    SALES_ORDER = "SalesOrder"
    DELIVERY_ORDER = "DeliveryOrder"
    INBOUND_ORDER = "InboundOrder"