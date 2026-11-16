import argparse
import os.path

import pytest

import ktp_controller.net
import ktp_controller.networking.dnsmasq
import ktp_controller.networking.main
import ktp_controller.networking.nm
import ktp_controller.nginx


def _domain_args(
    FQDN="host.example.invalid",
    nginx_port=None,
    nginx_crt_filepath=None,
    nginx_key_filepath=None,
):
    return argparse.Namespace(
        FQDN=FQDN,
        nginx_port=nginx_port,
        nginx_crt_filepath=nginx_crt_filepath,
        nginx_key_filepath=nginx_key_filepath,
    )


class TestRunRegardless:
    def test_returns_result_step_value_when_all_succeed(self):
        calls = []

        def step0():
            calls.append("step0")

        def step1():
            calls.append("step1")
            return "value"

        result = ktp_controller.networking.main._run_regardless(
            [step0, step1], result_index=1
        )

        assert result == "value"
        assert calls == ["step0", "step1"]

    def test_swallows_failure_before_result_step(self):
        def step0():
            raise ValueError("boom")

        def step1():
            return "value"

        result = ktp_controller.networking.main._run_regardless(
            [step0, step1], result_index=1
        )

        assert result == "value"

    def test_propagates_result_step_failure(self):
        def step0():
            pass

        def step1():
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            ktp_controller.networking.main._run_regardless(
                [step0, step1], result_index=1
            )

    def test_runs_cleanup_step_after_result_even_if_result_step_fails(self):
        calls = []

        def step0():
            calls.append("step0")

        def step1():
            calls.append("step1")
            raise ValueError("boom")

        def step2():
            calls.append("step2")

        with pytest.raises(ValueError, match="boom"):
            ktp_controller.networking.main._run_regardless(
                [step0, step1, step2], result_index=1
            )

        assert calls == ["step0", "step1", "step2"]

    def test_after_step_failure_overrides_already_computed_result(self):
        def step0():
            pass

        def step1():
            return "value"

        def step2():
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            ktp_controller.networking.main._run_regardless(
                [step0, step1, step2], result_index=1
            )

    def test_every_after_step_runs_even_if_an_earlier_one_fails(self):
        calls = []

        def step0():
            return "value"

        def step1():
            calls.append("step1")
            raise ValueError("boom")

        def step2():
            calls.append("step2")

        with pytest.raises(ValueError, match="boom"):
            ktp_controller.networking.main._run_regardless(
                [step0, step1, step2], result_index=0
            )

        assert calls == ["step1", "step2"]


class TestCommandStart:
    def test_happy_path_configures_nm_then_starts_dhcp_dns_server(self, mocker):
        net = mocker.Mock()
        mocker.patch("ktp_controller.net.Net", return_value=net)
        configure_mock = mocker.patch(
            "ktp_controller.networking.nm._configure_nm_dnsmasq_plugin"
        )
        start_mock = mocker.patch(
            "ktp_controller.networking.dnsmasq._start_dhcp_dns_server", return_value=0
        )
        mocker.patch(
            "ktp_controller.networking.dnsmasq._DNSMASQ_HOSTS_FILE", os.devnull
        )

        result = ktp_controller.networking.main._command_start(
            "eth0", "10.0.0.0/24", 0, _domain_args()
        )

        assert result == 0
        net.up.assert_called_once_with()
        configure_mock.assert_called_once_with()
        start_mock.assert_called_once_with(net)

    def test_dhcp_dns_server_still_started_when_configuring_nm_fails(self, mocker):
        net = mocker.Mock()
        mocker.patch("ktp_controller.net.Net", return_value=net)
        mocker.patch(
            "ktp_controller.networking.nm._configure_nm_dnsmasq_plugin",
            side_effect=OSError("boom"),
        )
        start_mock = mocker.patch(
            "ktp_controller.networking.dnsmasq._start_dhcp_dns_server", return_value=0
        )
        mocker.patch(
            "ktp_controller.networking.dnsmasq._DNSMASQ_HOSTS_FILE", os.devnull
        )

        result = ktp_controller.networking.main._command_start(
            "eth0", "10.0.0.0/24", 0, _domain_args()
        )

        assert result == 0
        start_mock.assert_called_once_with(net)


class TestCommandStop:
    def test_happy_path_unconfigures_nm_stops_dhcp_dns_server_and_brings_net_down(
        self, mocker
    ):
        net = mocker.Mock()
        mocker.patch("ktp_controller.net.Net", return_value=net)
        unconfigure_mock = mocker.patch(
            "ktp_controller.networking.nm._unconfigure_nm_dnsmasq_plugin"
        )
        stop_mock = mocker.patch(
            "ktp_controller.networking.dnsmasq._stop_dhcp_dns_server", return_value=0
        )

        result = ktp_controller.networking.main._command_stop(
            "eth0", "10.0.0.0/24", 0, _domain_args()
        )

        assert result == 0
        unconfigure_mock.assert_called_once_with()
        stop_mock.assert_called_once_with()
        net.down.assert_called_once_with()

    def test_net_down_failure_overrides_already_computed_result(self, mocker):
        net = mocker.Mock()
        net.down.side_effect = OSError("boom")
        mocker.patch("ktp_controller.net.Net", return_value=net)
        mocker.patch("ktp_controller.networking.nm._unconfigure_nm_dnsmasq_plugin")
        mocker.patch(
            "ktp_controller.networking.dnsmasq._stop_dhcp_dns_server", return_value=0
        )

        with pytest.raises(OSError, match="boom"):
            ktp_controller.networking.main._command_stop(
                "eth0", "10.0.0.0/24", 0, _domain_args()
            )


class TestCommandSetDomain:
    def test_rejects_partial_nginx_args_without_touching_networking(self, mocker):
        reload_mock = mocker.patch(
            "ktp_controller.networking.nm._reload_networkmanager"
        )

        result = ktp_controller.networking.main._command_set_domain(
            "eth0", "10.0.0.0/24", 0, _domain_args(nginx_port=443)
        )

        assert result == 1
        reload_mock.assert_not_called()

    def test_happy_path_writes_hosts_entry_and_signals_dnsmasq(self, mocker, testdir):
        hosts_filepath = os.path.join(testdir, "dnsmasq.hosts")
        mocker.patch(
            "ktp_controller.networking.dnsmasq._DNSMASQ_HOSTS_FILE", hosts_filepath
        )
        mocker.patch(
            "ktp_controller.net.interface_addresses",
            return_value={"AF_INET": [{"addr": "10.123.45.6"}]},
        )
        reload_mock = mocker.patch(
            "ktp_controller.networking.nm._reload_networkmanager"
        )
        enable_tls_mock = mocker.patch(
            "ktp_controller.nginx.enable_nginx_wui_tls_reverse_proxy"
        )
        kill_mock = mocker.patch(
            "ktp_controller.networking.dnsmasq._kill_dnsmasq", return_value=False
        )

        result = ktp_controller.networking.main._command_set_domain(
            "eth0", "10.0.0.0/24", 0, _domain_args(FQDN="host.example.invalid")
        )

        assert result == 0
        reload_mock.assert_called_once_with()
        enable_tls_mock.assert_not_called()
        kill_mock.assert_called_once()

        with open(hosts_filepath, encoding="utf-8") as hosts_file:
            assert hosts_file.read() == "10.123.45.6 host.example.invalid\n"

    def test_enables_nginx_tls_reverse_proxy_when_all_nginx_args_given(
        self, mocker, testdir
    ):
        hosts_filepath = os.path.join(testdir, "dnsmasq.hosts")
        mocker.patch(
            "ktp_controller.networking.dnsmasq._DNSMASQ_HOSTS_FILE", hosts_filepath
        )
        mocker.patch(
            "ktp_controller.net.interface_addresses",
            return_value={"AF_INET": [{"addr": "10.123.45.6"}]},
        )
        mocker.patch("ktp_controller.networking.nm._reload_networkmanager")
        enable_tls_mock = mocker.patch(
            "ktp_controller.nginx.enable_nginx_wui_tls_reverse_proxy"
        )
        mocker.patch(
            "ktp_controller.networking.dnsmasq._kill_dnsmasq", return_value=False
        )

        ktp_controller.networking.main._command_set_domain(
            "eth0",
            "10.0.0.0/24",
            0,
            _domain_args(
                FQDN="host.example.invalid",
                nginx_port=443,
                nginx_crt_filepath="/tmp/cert.pem",
                nginx_key_filepath="/tmp/key.pem",
            ),
        )

        enable_tls_mock.assert_called_once_with(
            "host.example.invalid", 443, "/tmp/cert.pem", "/tmp/key.pem"
        )

    def test_dnsmasq_still_signalled_when_reloading_nm_fails(self, mocker, testdir):
        hosts_filepath = os.path.join(testdir, "dnsmasq.hosts")
        mocker.patch(
            "ktp_controller.networking.dnsmasq._DNSMASQ_HOSTS_FILE", hosts_filepath
        )
        mocker.patch(
            "ktp_controller.net.interface_addresses",
            return_value={"AF_INET": [{"addr": "10.123.45.6"}]},
        )
        mocker.patch(
            "ktp_controller.networking.nm._reload_networkmanager",
            side_effect=OSError("boom"),
        )
        kill_mock = mocker.patch(
            "ktp_controller.networking.dnsmasq._kill_dnsmasq", return_value=True
        )

        result = ktp_controller.networking.main._command_set_domain(
            "eth0", "10.0.0.0/24", 0, _domain_args(FQDN="host.example.invalid")
        )

        assert result == 1
        kill_mock.assert_called_once()


class TestCommandDelDomain:
    def test_happy_path_truncates_hosts_file_and_signals_dnsmasq(self, mocker, testdir):
        hosts_filepath = os.path.join(testdir, "dnsmasq.hosts")
        with open(hosts_filepath, "w", encoding="utf-8") as hosts_file:
            hosts_file.write("10.123.45.6 host.example.invalid\n")
        mocker.patch(
            "ktp_controller.networking.dnsmasq._DNSMASQ_HOSTS_FILE", hosts_filepath
        )
        reload_mock = mocker.patch(
            "ktp_controller.networking.nm._reload_networkmanager"
        )
        disable_tls_mock = mocker.patch(
            "ktp_controller.nginx.disable_nginx_wui_tls_reverse_proxy"
        )
        kill_mock = mocker.patch(
            "ktp_controller.networking.dnsmasq._kill_dnsmasq", return_value=False
        )

        result = ktp_controller.networking.main._command_del_domain(
            "eth0", "10.0.0.0/24", 0, _domain_args()
        )

        assert result == 0
        reload_mock.assert_called_once_with()
        disable_tls_mock.assert_called_once_with()
        kill_mock.assert_called_once()

        with open(hosts_filepath, encoding="utf-8") as hosts_file:
            assert hosts_file.read() == ""

    def test_dnsmasq_still_signalled_when_reloading_nm_fails(self, mocker, testdir):
        hosts_filepath = os.path.join(testdir, "dnsmasq.hosts")
        mocker.patch(
            "ktp_controller.networking.dnsmasq._DNSMASQ_HOSTS_FILE", hosts_filepath
        )
        mocker.patch(
            "ktp_controller.networking.nm._reload_networkmanager",
            side_effect=OSError("boom"),
        )
        mocker.patch("ktp_controller.nginx.disable_nginx_wui_tls_reverse_proxy")
        kill_mock = mocker.patch(
            "ktp_controller.networking.dnsmasq._kill_dnsmasq", return_value=True
        )

        result = ktp_controller.networking.main._command_del_domain(
            "eth0", "10.0.0.0/24", 0, _domain_args()
        )

        assert result == 1
        kill_mock.assert_called_once()
