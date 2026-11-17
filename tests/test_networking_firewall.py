import pytest

import ktp_controller.networking.firewall


class TestRequireInterface:
    def test_passes_for_existing_interface(self, mocker):
        mocker.patch("ktp_controller.net.interfaces", return_value=["eth0"])

        ktp_controller.networking.firewall.require_interface("eth0")

    def test_raises_for_missing_interface(self, mocker):
        mocker.patch("ktp_controller.net.interfaces", return_value=["eth1"])

        with pytest.raises(ValueError, match="interface does not exist"):
            ktp_controller.networking.firewall.require_interface("eth0")

    def test_raises_for_empty_string(self, mocker):
        mocker.patch("ktp_controller.net.interfaces", return_value=["eth0"])

        with pytest.raises(ValueError, match="interface does not exist"):
            ktp_controller.networking.firewall.require_interface("")

    def test_raises_for_none(self, mocker):
        mocker.patch("ktp_controller.net.interfaces", return_value=["eth0"])

        with pytest.raises(ValueError, match="interface does not exist"):
            ktp_controller.networking.firewall.require_interface(None)


class TestChainExists:
    def test_returns_true_when_iptables_list_succeeds(self, mocker):
        run_mock = mocker.patch(
            "ktp_controller.networking.firewall.subprocess.run",
            return_value=mocker.Mock(returncode=0),
        )

        exists = ktp_controller.networking.firewall.chain_exists("filter", "mychain")

        assert exists is True
        run_mock.assert_called_once_with(
            ["iptables", "-t", "filter", "-L", "mychain", "-n"],
            capture_output=True,
        )

    def test_returns_false_when_iptables_list_fails(self, mocker):
        mocker.patch(
            "ktp_controller.networking.firewall.subprocess.run",
            return_value=mocker.Mock(returncode=1),
        )

        exists = ktp_controller.networking.firewall.chain_exists("filter", "mychain")

        assert exists is False


class TestChainManagement:
    def test_create_chain_invokes_iptables_new_chain(self, mocker):
        check_call_mock = mocker.patch(
            "ktp_controller.networking.firewall.subprocess.check_call"
        )

        ktp_controller.networking.firewall.create_chain("filter", "mychain")

        check_call_mock.assert_called_once_with(
            ["iptables", "-t", "filter", "-N", "mychain"]
        )

    def test_flush_chain_invokes_iptables_flush(self, mocker):
        check_call_mock = mocker.patch(
            "ktp_controller.networking.firewall.subprocess.check_call"
        )

        ktp_controller.networking.firewall.flush_chain("filter", "mychain")

        check_call_mock.assert_called_once_with(
            ["iptables", "-t", "filter", "-F", "mychain"]
        )

    def test_delete_chain_invokes_iptables_delete_chain(self, mocker):
        check_call_mock = mocker.patch(
            "ktp_controller.networking.firewall.subprocess.check_call"
        )

        ktp_controller.networking.firewall.delete_chain("filter", "mychain")

        check_call_mock.assert_called_once_with(
            ["iptables", "-t", "filter", "-X", "mychain"]
        )

    def test_recreate_chain_flushes_and_deletes_existing_chain_before_creating(
        self, mocker
    ):
        mocker.patch(
            "ktp_controller.networking.firewall.chain_exists", return_value=True
        )
        flush_mock = mocker.patch("ktp_controller.networking.firewall.flush_chain")
        delete_mock = mocker.patch("ktp_controller.networking.firewall.delete_chain")
        create_mock = mocker.patch("ktp_controller.networking.firewall.create_chain")

        ktp_controller.networking.firewall.recreate_chain("filter", "mychain")

        flush_mock.assert_called_once_with("filter", "mychain")
        delete_mock.assert_called_once_with("filter", "mychain")
        create_mock.assert_called_once_with("filter", "mychain")

    def test_recreate_chain_just_creates_when_chain_does_not_exist(self, mocker):
        mocker.patch(
            "ktp_controller.networking.firewall.chain_exists", return_value=False
        )
        flush_mock = mocker.patch("ktp_controller.networking.firewall.flush_chain")
        delete_mock = mocker.patch("ktp_controller.networking.firewall.delete_chain")
        create_mock = mocker.patch("ktp_controller.networking.firewall.create_chain")

        ktp_controller.networking.firewall.recreate_chain("filter", "mychain")

        flush_mock.assert_not_called()
        delete_mock.assert_not_called()
        create_mock.assert_called_once_with("filter", "mychain")


class TestAddRule:
    def test_add_rule_invokes_iptables_append(self, mocker):
        check_call_mock = mocker.patch(
            "ktp_controller.networking.firewall.subprocess.check_call"
        )

        ktp_controller.networking.firewall.add_rule(
            "filter", "mychain", "--jump", "ACCEPT"
        )

        check_call_mock.assert_called_once_with(
            ["iptables", "-t", "filter", "-A", "mychain", "--jump", "ACCEPT"]
        )


class TestRemoveRulesByComment:
    def test_removes_matching_rule_by_switching_append_to_delete(self, mocker):
        # Real `iptables -S` only quotes a --comment value when it needs
        # quoting (e.g. contains spaces); our comments never do, so the
        # real output looks like this, unquoted.
        mocker.patch(
            "ktp_controller.networking.firewall.subprocess.check_output",
            return_value=(b"-A FORWARD -m comment --comment myset -j ACCEPT\n"),
        )
        check_call_mock = mocker.patch(
            "ktp_controller.networking.firewall.subprocess.check_call"
        )

        ktp_controller.networking.firewall.remove_rules_by_comment(
            "filter", "FORWARD", "myset"
        )

        check_call_mock.assert_called_once_with(
            [
                "iptables",
                "-t",
                "filter",
                "-D",
                "FORWARD",
                "-m",
                "comment",
                "--comment",
                "myset",
                "-j",
                "ACCEPT",
            ]
        )

    def test_removes_matching_rule_with_quoted_comment(self, mocker):
        mocker.patch(
            "ktp_controller.networking.firewall.subprocess.check_output",
            return_value=(b'-A FORWARD -m comment --comment "my set" -j ACCEPT\n'),
        )
        check_call_mock = mocker.patch(
            "ktp_controller.networking.firewall.subprocess.check_call"
        )

        ktp_controller.networking.firewall.remove_rules_by_comment(
            "filter", "FORWARD", "my set"
        )

        check_call_mock.assert_called_once_with(
            [
                "iptables",
                "-t",
                "filter",
                "-D",
                "FORWARD",
                "-m",
                "comment",
                "--comment",
                "my set",
                "-j",
                "ACCEPT",
            ]
        )

    def test_leaves_non_matching_rules_alone(self, mocker):
        mocker.patch(
            "ktp_controller.networking.firewall.subprocess.check_output",
            return_value=(b"-A FORWARD -m comment --comment othername -j ACCEPT\n"),
        )
        check_call_mock = mocker.patch(
            "ktp_controller.networking.firewall.subprocess.check_call"
        )

        ktp_controller.networking.firewall.remove_rules_by_comment(
            "filter", "FORWARD", "myset"
        )

        check_call_mock.assert_not_called()

    def test_leaves_rules_alone_whose_comment_only_contains_target_as_substring(
        self, mocker
    ):
        mocker.patch(
            "ktp_controller.networking.firewall.subprocess.check_output",
            return_value=(
                b"-A FORWARD -m comment --comment allow_myset_to_wan -j ACCEPT\n"
            ),
        )
        check_call_mock = mocker.patch(
            "ktp_controller.networking.firewall.subprocess.check_call"
        )

        ktp_controller.networking.firewall.remove_rules_by_comment(
            "filter", "FORWARD", "myset"
        )

        check_call_mock.assert_not_called()

    def test_no_matching_rules_is_a_noop(self, mocker):
        mocker.patch(
            "ktp_controller.networking.firewall.subprocess.check_output",
            return_value=b"-P FORWARD ACCEPT\n",
        )
        check_call_mock = mocker.patch(
            "ktp_controller.networking.firewall.subprocess.check_call"
        )

        ktp_controller.networking.firewall.remove_rules_by_comment(
            "filter", "FORWARD", "myset"
        )

        check_call_mock.assert_not_called()

    def test_removes_every_matching_rule(self, mocker):
        mocker.patch(
            "ktp_controller.networking.firewall.subprocess.check_output",
            return_value=(
                b"-A FORWARD -i eth0 -m comment --comment myset -j ACCEPT\n"
                b"-A FORWARD -i eth1 -m comment --comment myset -j DROP\n"
            ),
        )
        check_call_mock = mocker.patch(
            "ktp_controller.networking.firewall.subprocess.check_call"
        )

        ktp_controller.networking.firewall.remove_rules_by_comment(
            "filter", "FORWARD", "myset"
        )

        assert check_call_mock.call_count == 2


class TestFlushAndDeleteChain:
    def test_noop_when_chain_does_not_exist(self, mocker):
        mocker.patch(
            "ktp_controller.networking.firewall.chain_exists", return_value=False
        )
        flush_mock = mocker.patch("ktp_controller.networking.firewall.flush_chain")
        delete_mock = mocker.patch("ktp_controller.networking.firewall.delete_chain")

        ktp_controller.networking.firewall.flush_and_delete_chain("filter", "mychain")

        flush_mock.assert_not_called()
        delete_mock.assert_not_called()

    def test_flushes_and_deletes_when_chain_exists(self, mocker):
        mocker.patch(
            "ktp_controller.networking.firewall.chain_exists", return_value=True
        )
        flush_mock = mocker.patch("ktp_controller.networking.firewall.flush_chain")
        delete_mock = mocker.patch("ktp_controller.networking.firewall.delete_chain")

        ktp_controller.networking.firewall.flush_and_delete_chain("filter", "mychain")

        flush_mock.assert_called_once_with("filter", "mychain")
        delete_mock.assert_called_once_with("filter", "mychain")


class TestEnableForwarding:
    def _patch_primitives(self, mocker):
        mocker.patch(
            "ktp_controller.networking.firewall.require_interface",
        )
        return {
            "remove_rules_by_comment": mocker.patch(
                "ktp_controller.networking.firewall.remove_rules_by_comment"
            ),
            "recreate_chain": mocker.patch(
                "ktp_controller.networking.firewall.recreate_chain"
            ),
            "add_rule": mocker.patch("ktp_controller.networking.firewall.add_rule"),
        }

    def test_raises_when_wan_and_lan_are_the_same(self, mocker):
        self._patch_primitives(mocker)

        with pytest.raises(ValueError, match="must be different"):
            ktp_controller.networking.firewall.enable_forwarding(
                "eth0", "eth0", "myset"
            )

    def test_propagates_require_interface_failure(self, mocker):
        mocker.patch(
            "ktp_controller.networking.firewall.require_interface",
            side_effect=ValueError("interface does not exist"),
        )

        with pytest.raises(ValueError, match="interface does not exist"):
            ktp_controller.networking.firewall.enable_forwarding(
                "eth0", "eth1", "myset"
            )

    def test_recreates_chain_after_removing_old_comment_rules(self, mocker):
        mocks = self._patch_primitives(mocker)

        ktp_controller.networking.firewall.enable_forwarding("eth0", "eth1", "myset")

        assert mocks["remove_rules_by_comment"].call_args_list == [
            mocker.call("nat", "POSTROUTING", "myset"),
            mocker.call("filter", "FORWARD", "myset"),
        ]
        mocks["recreate_chain"].assert_called_once_with("filter", "myset")

    def test_adds_expected_rules(self, mocker):
        mocks = self._patch_primitives(mocker)

        ktp_controller.networking.firewall.enable_forwarding("eth0", "eth1", "myset")

        assert mocks["add_rule"].call_args_list == [
            mocker.call(
                "filter",
                "myset",
                "--match",
                "conntrack",
                "--ctstate",
                "NEW",
                "--match",
                "set",
                "--match-set",
                "myset",
                "dst",
                "--match",
                "limit",
                "--limit",
                "30/second",
                "--limit-burst",
                "100",
                "--jump",
                "LOG",
                "--log-prefix",
                "myset ",
                "--log-level",
                "6",
            ),
            mocker.call(
                "filter",
                "myset",
                "--match",
                "set",
                "--match-set",
                "myset",
                "dst",
                "--jump",
                "ACCEPT",
            ),
            mocker.call("filter", "myset", "--jump", "DROP"),
            mocker.call(
                "filter",
                "FORWARD",
                "--in-interface",
                "eth1",
                "--out-interface",
                "eth0",
                "--match",
                "comment",
                "--comment",
                "myset",
                "--match",
                "conntrack",
                "--ctstate",
                "RELATED,ESTABLISHED",
                "--jump",
                "ACCEPT",
            ),
            mocker.call(
                "filter",
                "FORWARD",
                "--in-interface",
                "eth0",
                "--out-interface",
                "eth1",
                "--match",
                "comment",
                "--comment",
                "myset",
                "--jump",
                "myset",
            ),
            mocker.call(
                "nat",
                "POSTROUTING",
                "--out-interface",
                "eth1",
                "--match",
                "comment",
                "--comment",
                "myset",
                "--match",
                "set",
                "--match-set",
                "myset",
                "dst",
                "--jump",
                "MASQUERADE",
            ),
        ]


class TestDisableForwarding:
    def test_removes_comment_rules_then_flushes_and_deletes_chain(self, mocker):
        remove_mock = mocker.patch(
            "ktp_controller.networking.firewall.remove_rules_by_comment"
        )
        flush_and_delete_mock = mocker.patch(
            "ktp_controller.networking.firewall.flush_and_delete_chain"
        )

        ktp_controller.networking.firewall.disable_forwarding("myset")

        assert remove_mock.call_args_list == [
            mocker.call("nat", "POSTROUTING", "myset"),
            mocker.call("filter", "FORWARD", "myset"),
        ]
        flush_and_delete_mock.assert_called_once_with("filter", "myset")
