import datetime

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

    assert fi_gettext("Log in") != "Log in"
    assert en_gettext("Log in") == "Log in"


def test_localize_date_differs_by_locale_format():
    d = datetime.date(2005, 1, 1)

    fi_str = i18n.localize_date(d, "fi")
    en_str = i18n.localize_date(d, "en")

    assert "." in fi_str
    assert fi_str != en_str


def test_translate_labels_falls_back_to_raw_value_when_unknown():
    assert i18n.translate_labels({"a", "b"}, {"a": "A"}) == "A, b"


def test_translate_labels_returns_dash_for_empty_set():
    assert i18n.translate_labels(set(), {}) == "-"
