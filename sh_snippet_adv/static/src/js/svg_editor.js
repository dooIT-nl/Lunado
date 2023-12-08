odoo.define("sh_snippet_adv.svg_editor", function (require) {
    "use strict";

    var core = require("web.core");
    const Dialog = require("web.Dialog");
    var options = require("web_editor.snippets.options");
    require('website.form_editor');

    const qweb = core.qweb;
    var _t = core._t;

    options.registry.shSnippetAdvTiltFeature = options.Class.extend({
        events:{
			'click .tilt_wrapper we-button':'_onClickTiltWrapper',
	    },

        _onClickTiltWrapper : function () {
            if(this.$target.attr('data-tilt-feature')){
                this.$target.attr('data-tilt','data-tilt')
                this.$target.parent().css("overflow","unset")
            }
            else{
                this.$target.removeAttr('data-tilt')
                this.$target.parent().css("overflow","hidden")
            }
        },
    });
    options.registry.sh_snippet_adv_svg_editor = options.Class.extend({
        /**
         * Allows to select a font awesome icon with media dialog.
         *
         * @see this.selectClass for parameters
         */
        changeSvg: async function (previewMode, widgetValue, params) {
            var self = this;
            if (this.$target && this.$target.find("svg").length) {
                // OPEN DIALOG FOR CHANGE SVG
                var buttons = [
                    {
                        text: _t("Replace SVG"),
                        close: true,
                        classes: "btn-primary",
                        click: function () {
                            var svg_code = this.$content.find("textarea").val();
                            svg_code = svg_code.trim();
                            if (svg_code.length) {
                                svg_code = $(svg_code);
                                self.$target.find("svg").replaceWith(svg_code);
                            }
                        },
                    },
                    {
                        text: _t("Close"),
                        classes: "btn-secondary",
                        close: true,
                    },
                ];

                var $content = $("<div/>").append($('<textarea rows="8" cols="70"/>'));

                var dialog = new Dialog(this, {
                    size: "medium",
                    buttons: buttons,
                    $content: $content,
                    title: _t("Replace SVG"),
                });
                dialog.open();
            }
        },
    });
});
