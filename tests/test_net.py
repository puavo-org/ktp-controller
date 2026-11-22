import os.path
import subprocess

import ktp_controller.net

_DEFAULT_ROUTE_OUTPUT = b"default via 192.168.1.1 dev eth0 proto dhcp metric 100\n"


def _subprocess_check_output_side_effect(*, nmcli_output=b"", nmcli_error=None):
    def side_effect(args, timeout=None):
        if args[0] == "ip":
            return _DEFAULT_ROUTE_OUTPUT
        if args[0] == "nmcli":
            if nmcli_error is not None:
                raise nmcli_error
            return nmcli_output
        raise AssertionError(f"unexpected command: {args}")

    return side_effect


def _write_resolv_conf(testdir, monkeypatch, lines):
    resolv_conf_filepath = os.path.join(testdir, "resolv.conf")
    with open(resolv_conf_filepath, "w", encoding="utf-8") as resolv_conf_file:
        for line in lines:
            print(line, file=resolv_conf_file)
    monkeypatch.setattr(
        ktp_controller.net, "_RESOLV_CONF_FILEPATH", resolv_conf_filepath
    )


def test_get_default_route_interface_returns_device_from_default_route(mocker):
    output = b"default via 192.168.1.1 dev eth0 proto dhcp metric 100\n"
    check_output_mock = mocker.patch(
        "ktp_controller.net.subprocess.check_output",
        return_value=output,
    )

    interface = ktp_controller.net.get_default_route_interface()

    assert interface == "eth0"
    check_output_mock.assert_called_once_with(
        ["ip", "route", "show", "default"], timeout=2
    )


def test_get_default_route_interface_returns_none_when_no_default_route(mocker):
    mocker.patch(
        "ktp_controller.net.subprocess.check_output",
        return_value=b"",
    )

    interface = ktp_controller.net.get_default_route_interface()

    assert interface is None


def test_get_default_nameservers_combines_nmcli_and_resolv_conf(
    mocker, testdir, monkeypatch
):
    mocker.patch(
        "ktp_controller.net.subprocess.check_output",
        side_effect=_subprocess_check_output_side_effect(
            nmcli_output=b"IP4.DNS[1]:8.8.4.4\n"
        ),
    )
    _write_resolv_conf(testdir, monkeypatch, ["nameserver 9.9.9.9"])

    assert ktp_controller.net.get_default_nameservers() == ["8.8.4.4", "9.9.9.9"]


def test_get_default_nameservers_filters_out_loopback_addresses(
    mocker, testdir, monkeypatch
):
    mocker.patch(
        "ktp_controller.net.subprocess.check_output",
        side_effect=_subprocess_check_output_side_effect(
            nmcli_output=b"IP4.DNS[1]:127.0.0.1\n"
        ),
    )
    _write_resolv_conf(testdir, monkeypatch, ["nameserver 127.0.0.53"])

    assert ktp_controller.net.get_default_nameservers() == []


def test_get_default_nameservers_deduplicates_across_sources(
    mocker, testdir, monkeypatch
):
    mocker.patch(
        "ktp_controller.net.subprocess.check_output",
        side_effect=_subprocess_check_output_side_effect(
            nmcli_output=b"IP4.DNS[1]:8.8.4.4\n"
        ),
    )
    _write_resolv_conf(testdir, monkeypatch, ["nameserver 8.8.4.4"])

    assert ktp_controller.net.get_default_nameservers() == ["8.8.4.4"]


def test_get_default_nameservers_falls_back_to_resolv_conf_without_default_route(
    mocker, testdir, monkeypatch
):
    check_output_mock = mocker.patch(
        "ktp_controller.net.subprocess.check_output",
        return_value=b"",
    )
    _write_resolv_conf(testdir, monkeypatch, ["nameserver 1.1.1.1"])

    assert ktp_controller.net.get_default_nameservers() == ["1.1.1.1"]
    check_output_mock.assert_called_once_with(
        ["ip", "route", "show", "default"], timeout=2
    )


def test_get_default_nameservers_tolerates_missing_nmcli_binary(
    mocker, testdir, monkeypatch
):
    mocker.patch(
        "ktp_controller.net.subprocess.check_output",
        side_effect=_subprocess_check_output_side_effect(
            nmcli_error=FileNotFoundError()
        ),
    )
    _write_resolv_conf(testdir, monkeypatch, ["nameserver 1.1.1.1"])

    assert ktp_controller.net.get_default_nameservers() == ["1.1.1.1"]


def test_get_default_nameservers_tolerates_failing_nmcli_command(
    mocker, testdir, monkeypatch
):
    mocker.patch(
        "ktp_controller.net.subprocess.check_output",
        side_effect=_subprocess_check_output_side_effect(
            nmcli_error=subprocess.CalledProcessError(1, ["nmcli"])
        ),
    )
    _write_resolv_conf(testdir, monkeypatch, ["nameserver 1.1.1.1"])

    assert ktp_controller.net.get_default_nameservers() == ["1.1.1.1"]


def test_get_default_nameservers_tolerates_missing_resolv_conf(
    mocker, testdir, monkeypatch
):
    mocker.patch(
        "ktp_controller.net.subprocess.check_output",
        side_effect=_subprocess_check_output_side_effect(
            nmcli_output=b"IP4.DNS[1]:8.8.4.4\n"
        ),
    )
    monkeypatch.setattr(
        ktp_controller.net,
        "_RESOLV_CONF_FILEPATH",
        os.path.join(testdir, "nonexistent-resolv.conf"),
    )

    assert ktp_controller.net.get_default_nameservers() == ["8.8.4.4"]
