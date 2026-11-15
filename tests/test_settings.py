import pydantic
import pytest

import ktp_controller.settings


def _make_settings(**overrides: object) -> ktp_controller.settings.Settings:
    kwargs: dict[str, object] = {
        "examomatic_host": "examomatic.example.invalid",
        "examomatic_username": "user",
        "examomatic_password_file": "/dev/null",
        "domain": "example.invalid",
        "id": 1,
    }
    kwargs.update(overrides)
    return ktp_controller.settings.Settings(**kwargs)


def test_networking_allowed_wan_domains_default():
    settings = _make_settings()
    assert settings.networking_allowed_wan_domains == [
        "dns.msftncsi.com",
        "www.msftncsi.com",
        "www.msftconnecttest.com",
        "ipv6.msftconnecttest.com",
        "endpoint.security.microsoft.com",
        "smartscreen-prod.microsoft.com",
        "smartscreen.microsoft.com",
        "wdcp.microsoft.com",
        "wdcpalt.microsoft.com",
        "wd.microsoft.com",
        "ctldl.windowsupdate.com",
        "crl.microsoft.com",
        "chromeos-staging.abitti.fi",
        "chromeos.abitti.fi",
        "register.appattest.apple.com",
        "m.google.com",
        "chromeos-ca.gstatic.com",
        "clients3.google.com",
        "www.googleapis.com",
    ]


def test_networking_allowed_wan_domains_accepts_comma_separated_string():
    settings = _make_settings(
        networking_allowed_wan_domains="example.com, foo.example.org"
    )
    assert settings.networking_allowed_wan_domains == ["example.com", "foo.example.org"]


def test_networking_allowed_wan_domains_rejects_invalid_domain_in_list():
    with pytest.raises(pydantic.ValidationError):
        _make_settings(networking_allowed_wan_domains=["not a domain"])


def test_networking_allowed_wan_domains_rejects_invalid_domain_in_string():
    with pytest.raises(pydantic.ValidationError):
        _make_settings(networking_allowed_wan_domains="example.com, not a domain")
