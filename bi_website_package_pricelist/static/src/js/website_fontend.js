/** @odoo-module **/

import publicWidget from "web.public.widget";
import "website_sale.website_sale";
import ajax from "web.ajax";
import { qweb as QWeb } from "web.core";

publicWidget.registry.WebsiteSale.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _submitForm: function(e) {
        var qty_val = $('.selected_package_value').attr('id')
        this.rootProduct.product_packaging_id = parseInt(qty_val)
        return this._super(...arguments);
    },
});