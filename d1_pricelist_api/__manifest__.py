{
    "name": "Pricelist Price API",
    "summary": "Public JSON-2 API method to compute customer pricelist prices",
    "version": "19.0.1.1.0",
    "category": "Sales/Sales",
    "author": "dooIT B.V.",
    "website": "https://dooit.nl",
    "license": "LGPL-3",
    "depends": ["product"],
    "data": [
        "security/ir.model.access.csv",
    ],
    "installable": True,
    "application": False,
    "description": """
        Pricelist Price API 19.0.1.1.0
        ==============================
        * v1.1: response now includes default_code (internal reference) so
          callers can verify the resolved product variant.
        * v1.0: initial release — public method d1_api_get_customer_price on
          product.pricelist, exposing the internal pricelist price computation
          (excl. VAT, tiered pricing supported) to external systems via the
          Odoo 19 JSON-2 API.
    """,
}
