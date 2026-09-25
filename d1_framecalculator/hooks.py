"""Post-init hook: neem de configuratie over uit de oude handmatige
serveractie en ruim die op.

De oude serveractie (handmatig aangemaakt op sale.order) bevatte de
framecalculator-URL en de API-key hardcoded in de Python-code. Bij
installatie:

1. wordt die serveractie opgezocht (code bevat 'framecalculator');
2. worden URL en API-key eruit geparsed en — alleen als de instellingen nog
   leeg zijn — opgeslagen als systeemparameters (de key wordt gedecodeerd:
   in de actie stond hij URL-encoded);
3. wordt de serveractie verwijderd en worden knop-verwijzingen ernaar uit
   nog actieve Studio-views geknipt.

Op een database zonder die serveractie (dev) gebeurt er niets; de
instellingen blijven dan leeg en de knop geeft een duidelijke melding.
"""
import logging
import re
from urllib.parse import unquote

from lxml import etree

_logger = logging.getLogger(__name__)

MODULE = "d1_framecalculator"
PARAM_URL = "d1_framecalculator.url"
PARAM_KEY = "d1_framecalculator.api_key"


def _find_legacy_actions(env):
    """Zoek de handmatige serveractie(s) met de framecalculator-URL."""
    return env["ir.actions.server"].search(
        [
            ("state", "=", "code"),
            ("model_id.model", "=", "sale.order"),
            ("code", "ilike", "framecalculator"),
        ]
    )


def _take_over_configuration(env, actions):
    """Parse URL en API-key uit de actiecode en zet ze als systeemparameters
    (alleen als die nog niet gevuld zijn)."""
    params = env["ir.config_parameter"].sudo()
    for action in actions:
        code = action.code or ""
        url_match = re.search(r'https://[^"\s?]+', code)
        key_match = re.search(r'apikey=([^&"\s{]+)', code)
        if url_match and not params.get_param(PARAM_URL):
            params.set_param(PARAM_URL, url_match.group(0))
            _logger.info("%s: took over framecalculator URL from server "
                         "action '%s'", MODULE, action.name)
        if key_match and not params.get_param(PARAM_KEY):
            # de key stond URL-encoded in de f-string; opslaan als platte key
            params.set_param(PARAM_KEY, unquote(key_match.group(1)))
            _logger.info("%s: took over framecalculator API key from server "
                         "action '%s'", MODULE, action.name)


def _strip_button_from_views(env, action_ids):
    """Knip knoppen die naar de oude serveractie verwijzen uit nog actieve
    Studio-views (de module levert zijn eigen knop)."""
    for action_id in action_ids:
        views = env["ir.ui.view"].search(
            [
                ("model", "=", "sale.order"),
                ("arch_db", "like", 'name="%s"' % action_id),
            ]
        )
        for view in views:
            xml_id = view.get_external_id().get(view.id) or ""
            if not xml_id.startswith("studio_customization."):
                continue
            try:
                arch = etree.fromstring(view.arch_db.encode("utf-8"))
                nodes = arch.xpath(
                    "//button[@name='%s'][@type='action']" % action_id
                )
                if not nodes:
                    continue
                for node in nodes:
                    node.getparent().remove(node)
                view.arch_db = etree.tostring(arch, encoding="unicode")
                _logger.info("%s: stripped legacy button from view %s",
                             MODULE, xml_id)
            except Exception as exc:
                _logger.warning(
                    "%s: could not strip legacy button from view %s (%s); "
                    "deactivating view", MODULE, xml_id, exc)
                view.active = False


def _remove_legacy_actions(env, actions):
    """Verwijder de oude serveractie(s), inclusief eventuele contextuele
    binding."""
    for action in actions:
        name = action.name
        try:
            action.unlink()
            _logger.info("%s: removed legacy server action '%s'", MODULE,
                         name)
        except Exception as exc:
            _logger.warning("%s: could not remove legacy server action "
                            "'%s' (%s); please clean up manually",
                            MODULE, name, exc)


def post_init_hook(env):
    """Neem de framecalculator-configuratie over en ruim de oude
    serveractie op."""
    actions = _find_legacy_actions(env)
    if not actions:
        _logger.info("%s: no legacy framecalculator server action found",
                     MODULE)
        return
    _take_over_configuration(env, actions)
    _strip_button_from_views(env, actions.ids)
    _remove_legacy_actions(env, actions)
