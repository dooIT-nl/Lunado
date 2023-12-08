# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.
{
    "name": "Snippet Advance Settings",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "version": "16.0.3",
    "category": "Website",
    "summary": "Set Custom Snippets, Animation Snippet, Snippet Animation, Custom Snippet Module, Custom Color, Set Different Hover At Snippet, Custom Border In Snippet, Custom Stylish Snippets, Animation On Snippets, snippet settings Odoo",
    "description": """This module provides some utility features that extend the functionality of the web editor. You can set custom styles for your snippet. You can set a box-shadow, box-shadow hover, border style, custom border width, border color, border-radius, custom background-color.
    """,
    "depends": [
        "web_editor",
        "website"
    ],
    "data": [
        "views/web_editor.xml",
    ],

    'assets': {
        'web_editor.assets_wysiwyg': [
            "sh_snippet_adv/static/src/scss/snippets_options.scss",
            'sh_snippet_adv/static/src/js/svg_editor.js',
        ],

        'web.assets_frontend': [
            'sh_snippet_adv/static/src/scss/image_mask.scss',
            "sh_snippet_adv/static/src/libs/owl/owl.carousel.min.css",
            "sh_snippet_adv/static/src/libs/owl/owl.theme.default.min.css",
            "sh_snippet_adv/static/src/libs/aos/aos.css",
            "sh_snippet_adv/static/src/libs/aos/aos_extra.css",
            "sh_snippet_adv/static/src/libs/aos/layout.css",
            "sh_snippet_adv/static/src/libs/owl/owl.carousel.js",
            "sh_snippet_adv/static/src/libs/aos/aos.js",
            "sh_snippet_adv/static/src/js/s_animation.js",
            "sh_snippet_adv/static/src/js/tilt.js",
        ]},
    "images": ["static/description/background.png", ],
    "installable": True,
    "application": True,
    "autoinstall": False,
    "price": 1,
    "currency": "EUR",
    "license": "OPL-1"
}
