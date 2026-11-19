import pydantic
import pytest
import validators

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
    assert len(settings.networking_allowed_wan_domains) > 1
    assert all(validators.domain(d) for d in settings.networking_allowed_wan_domains)


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
