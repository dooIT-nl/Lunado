odoo.define("sh_snippet_adv.sh_snippet_adv_s_animation", function (require) {
    "use strict";

    var publicWidget = require("web.public.widget");
    var registry = publicWidget.registry;
    var animations = require("website.content.snippets.animation");

    AOS.init({});

    function isElementPartiallyInViewport(el) {
        // Special bonus for those using jQuery
        if (typeof jQuery !== "undefined" && el instanceof jQuery) el = el[0];

        var rect = el.getBoundingClientRect();
        // DOMRect { x: 8, y: 8, width: 100, height: 100, top: 8, right: 108, bottom: 108, left: 8 }
        var windowHeight = window.innerHeight || document.documentElement.clientHeight;
        var windowWidth = window.innerWidth || document.documentElement.clientWidth;

        // http://stackoverflow.com/questions/325933/determine-whether-two-date-ranges-overlap
        var vertInView = rect.top <= windowHeight && rect.top + rect.height >= 0;
        var horInView = rect.left <= windowWidth && rect.left + rect.width >= 0;

        return vertInView && horInView;
    }

    //Helper function from: http://stackoverflow.com/a/7557433/274826
    function isElementInViewport(el) {
        // special bonus for those using jQuery
        if (typeof jQuery === "function" && el instanceof jQuery) {
            el = el[0];
        }
        var rect = el.getBoundingClientRect();
        return (
            (rect.top <= 0 && rect.bottom >= 0) ||
            (rect.bottom >= (window.innerHeight || document.documentElement.clientHeight) && rect.top <= (window.innerHeight || document.documentElement.clientHeight)) ||
            (rect.top >= 0 && rect.bottom <= (window.innerHeight || document.documentElement.clientHeight))
        );
    }

    registry.sAnimationWidget = animations.Animation.extend({
        selector: ".aos-init",
        disabledInEditableMode: true,
        effects: [
            {
                startEvents: "scroll",
                update: "_updateCounterOnScroll",
            },
        ],

        /**
         * @constructor
         */
        init: function () {
            this._super(...arguments);
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------
        /**
         * Called when the window is scrolled
         *
         * @private
         * @param {integer} scroll
         */
        _updateCounterOnScroll: function (scroll) {
            if (isElementPartiallyInViewport(this.$el)) {
                this.$el.addClass("aos-animate");
            } else {
                this.$el.removeClass("aos-animate");
            }
        },
    });
});
