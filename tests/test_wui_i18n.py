import ktp_controller.wui.i18n as i18n
from ktp_controller import SETTINGS


def test_negotiate_locale_prefers_highest_q_value():
    assert i18n.negotiate_locale("en;q=0.5,fi;q=0.9") == "fi"


def test_negotiate_locale_falls_back_to_default_when_unsupported():
    assert i18n.negotiate_locale("de") == SETTINGS.default_locale


def test_negotiate_locale_falls_back_to_default_when_header_absent():
    assert i18n.negotiate_locale(None) == SETTINGS.default_locale
    assert i18n.negotiate_locale("") == SETTINGS.default_locale


def test_compiled_catalogs_translate_known_strings():
    fi_gettext = i18n.get_gettext("fi")
    en_gettext = i18n.get_gettext("en")

    assert fi_gettext("Log in") == "Kirjaudu sisään"
    assert en_gettext("Log in") == "Log in"
