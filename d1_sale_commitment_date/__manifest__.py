{
    "name": "Sale Commitment Date from Order Lines",
    "summary": "Compute the sale order delivery date from stock, incoming receipts and customer lead time",
    "version": "19.0.1.0.1",
    "category": "Sales",
    "author": "dooIT B.V.",
    "website": "https://dooit.nl",
    "license": "LGPL-3",
    "depends": ["sale_stock", "mrp"],
    "data": [
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "application": False,
    "description": """
        Sale Commitment Date from Order Lines 19.0.1.0.1
        ================================================
        * v1.0.1: velden met eigen label in de Delivery-sectie geplaatst
          (stonden labelloos in de Delivery Date-rij en waren onzichtbaar)
        * v1.0: initiele versie — berekening commitment_date per orderregel
          (vrije voorraad / eerstvolgende ontvangst / sale_delay), stuklijst-
          explosie voor kit- en productieartikelen, gewenste leverdatum klant
          met waarschuwingsbanner.
    """,
}
