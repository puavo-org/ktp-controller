import ipaddress
import os.path

import ktp_controller.networking.dnsmasq


class _FakeNet:
    def __init__(self) -> None:
        self.host_address = ipaddress.IPv4Address("10.123.45.1")
        self.network = ipaddress.IPv4Network("10.123.45.0/24")
        self.dhcp_hosts = [
            ipaddress.IPv4Address("10.123.45.10"),
            ipaddress.IPv4Address("10.123.45.254"),
        ]


def test_start_dhcp_dns_server_writes_conf_file_and_invokes_dnsmasq(
    mocker, testdir, monkeypatch
):
    conf_filepath = os.path.join(testdir, "dnsmasq.conf")
    monkeypatch.setattr(
        ktp_controller.networking.dnsmasq, "_DNSMASQ_CONF_FILE", conf_filepath
    )
    monkeypatch.delenv("SUDO_USER", raising=False)

    check_call_mock = mocker.patch(
        "ktp_controller.networking.dnsmasq.subprocess.check_call", return_value=None
    )

    result = ktp_controller.networking.dnsmasq._start_dhcp_dns_server(_FakeNet())

    assert result == 0
    check_call_mock.assert_called_once_with(["dnsmasq", f"--conf-file={conf_filepath}"])

    with open(conf_filepath, encoding="utf-8") as conf_file:
        conf_lines = conf_file.read().splitlines()

    assert conf_lines == [
        "port=53",
        "listen-address=10.123.45.1",
        "domain=koe.abitti.net,10.123.45.0/24",
        "domain-needed",
        "bogus-priv",
        "no-hosts",
        "bind-interfaces",
        "except-interface=lo",
        f"dhcp-leasefile={ktp_controller.networking.dnsmasq._DNSMASQ_LEASES_FILE}",
        "dhcp-range=10.123.45.10,10.123.45.254,1h",
        "dhcp-option=option:dns-server,10.123.45.1",
        "dhcp-option=option:domain-name",
        "log-queries",
        "log-dhcp",
        "log-debug",
        f"pid-file={ktp_controller.networking.dnsmasq._DNSMASQ_PID_FILE}",
        f"addn-hosts={ktp_controller.networking.dnsmasq._DNSMASQ_HOSTS_FILE}",
        "server=/koe.abitti.net/9.9.9.9",
        "server=/koe.abitti.net/1.1.1.1",
        "server=/koe.abitti.net/8.8.8.8",
        "all-servers",
    ]


def test_start_dhcp_dns_server_adds_user_option_from_sudo_user(
    mocker, testdir, monkeypatch
):
    conf_filepath = os.path.join(testdir, "dnsmasq.conf")
    monkeypatch.setattr(
        ktp_controller.networking.dnsmasq, "_DNSMASQ_CONF_FILE", conf_filepath
    )
    monkeypatch.setenv("SUDO_USER", "someuser")

    mocker.patch(
        "ktp_controller.networking.dnsmasq.subprocess.check_output",
        return_value=b"someuser\n",
    )
    mocker.patch(
        "ktp_controller.networking.dnsmasq.subprocess.check_call", return_value=None
    )

    ktp_controller.networking.dnsmasq._start_dhcp_dns_server(_FakeNet())

    with open(conf_filepath, encoding="utf-8") as conf_file:
        conf_lines = conf_file.read().splitlines()

    assert conf_lines[-1] == "user=someuser"
