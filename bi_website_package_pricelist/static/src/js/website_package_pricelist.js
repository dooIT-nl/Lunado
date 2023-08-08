odoo.define('bi_website_package_pricelist.product_package_pricelist', function(require) {
    'use strict';
    var ajax = require('web.ajax');
    $(document).ready(function(e) {
        $(".package_pricelist").on("click", function(e) {
            var qty_val = $(e.currentTarget).attr('id')
            $('input').removeClass('selected_package_value');
            $(e.currentTarget).addClass('selected_package_value')
            ajax.jsonRpc("/shop/product/packaging", 'call', { 'qty_val': qty_val })
                .then(function(actionData) {
                    if (actionData != false) {
                        $('.pricelist_price_Label').removeClass('d-none');
                        $('.priceslist_price').removeClass('d-none');
                        $('.priceslist_price').val(actionData.toFixed(2));
                    } else {
                        $('.pricelist_price_Label').removeClass('d-none');
                        $('.priceslist_price').removeClass('d-none');
                        $('.priceslist_price').val(0.0);
                    }
                });
        });
    })
});