odoo.define("sh_category_snippet.s_category", function (require) {
    var concurrency = require("web.concurrency");
    var core = require("web.core");
    var publicWidget = require("web.public.widget");

    var qweb = core.qweb;


    publicWidget.registry.sh_category_snippet = publicWidget.Widget.extend({
		selector: ".js_cls_get_sh_categ_s_category",
		disabledInEditableMode: true,
		/**
         * @constructor
         */
        init: function () {
            this._super.apply(this, arguments);
            this._dp = new concurrency.DropPrevious();
        },
        /**
         * @override
         */
        start: function () {
			
			this.class_name = this.$el.attr("class");
            this.item_template = this.$el.attr("data-item_template") ;
            this.owl_item_mobile = parseInt(this.$el.attr("data-owl_item_mobile")) || 1;
            this.owl_item_tablet = parseInt(this.$el.attr("data-owl_item_tablet")) || 3;
            this.owl_item_desktop = parseInt(this.$el.attr("data-owl_item_desktop")) || 5;
            this.categs_ids = [];

            this.order_by = this.$el.attr("data-order") || false;
            this.is_show_categ_image = !!this.$el.data("displayImage");
            this.is_show_categ_desc = !!this.$el.data("displayDescription");
            this.is_show_categ_prod_count = !!this.$el.data("displayProductCount");

          if(this.$el.hasClass( "name_asc" )){
	    			this.order_by = 'name asc';
	    		}  	   
	    		
	    		if(this.$el.hasClass( "name_desc" )){
	    			this.order_by = 'name desc';
	    		}  	   
	    		
	    		if(this.$el.hasClass( "create_date_asc" )){
	    			this.order_by = 'create_date asc';
	    		}  	   
	    		
	    		if(this.$el.hasClass( "create_date_desc" )){
	    			this.order_by = 'create_date desc';
	    		}  	   
	    		
	    		if(this.$el.hasClass( "sequence_asc" )){
	    			this.order_by = 'sequence asc';
	    		}  	   
	    		
	    		if(this.$el.hasClass( "sequence_desc" )){
	    			this.order_by = 'sequence desc';
	    		}  	
	    		
	    		//add to cart
	    		if(this.$el.hasClass( "is_show_categ_image" )){
	    			this.is_show_categ_image = true;
	    		}
	    		
	    		//product description
	    		if(this.$el.hasClass( "is_show_categ_desc" )){
	    			this.is_show_categ_desc = true;
	    		}

	    		//sale price
	    		if(this.$el.hasClass( "is_show_categ_prod_count" )){
	    			this.is_show_categ_prod_count = true;
	    		}
 			
			//get snippet options
            var class_name = this.$el.attr("class");
            if (class_name) {
                //for category
				var categs_ids = [];
                var myStringArray = class_name.split(" ");
                var arrayLength = myStringArray.length;
                for (var i = 0; i < arrayLength; i++) {
                    var js_categ_id = myStringArray[i].match("sh_categ_snipp_(.*)_cend");
                    if (js_categ_id && js_categ_id.length == 2) {
                        categs_ids.push(parseInt( js_categ_id[1]));
                    }
                }
                this.categs_ids = categs_ids;


            }

            this._dp.add(this._fetch()).then(this._render.bind(this));
            return this._super.apply(this, arguments);
		
        },

		destroy: function () {
			this._super(...arguments);
			//this.$el.find('.js_cls_render_dynamic_categs_dropdown_menu').html('');
			this.$el.find('.js_cls_render_dynamic_category_area').empty();  
		},



		/**
         * @private
         */
        _fetch: function (values) {
			// Add dynamic content
            return this._rpc({
                route: "/sh_category_snippet/get_categories",
                params: {
					item_template: this.item_template,
	                categs_ids: this.categs_ids,
	                order_by: this.order_by,
	                is_show_categ_image: this.is_show_categ_image,
	                is_show_categ_desc: this.is_show_categ_desc,
	                is_show_categ_prod_count: this.is_show_categ_prod_count,
                  
                },
            }).then((res) => {
                return res;
            });
        },
		
		/**
         * @private
         */
        _render: function (res) {
            // Add dynamic content
			this.$(".js_cls_render_dynamic_category_area").html(res.data);

            //refresh the owl start here
			this.$(".owl-carousel").owlCarousel({
                autoplay: true,
                autoplayTimeout: 5000,
                loop: true,
                nav: true,
				dots: false,
                items: 4,
                navigation: true,
                responsive: {
                    0: {
                        items: this.owl_item_mobile,
                        nav: true,
                    },
                    760: {
                        items: this.owl_item_tablet,
                        nav: false,
                    },
                    1000: {
                        items: this.owl_item_desktop,
                        nav: true,
                    },
                },
            });
        },
	
	});
});
