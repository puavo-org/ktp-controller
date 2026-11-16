import ktp_controller.networking.ipset


def test_create_ipset_invokes_ipset_create(mocker):
    check_call_mock = mocker.patch(
        "ktp_controller.networking.ipset.subprocess.check_call", return_value=None
    )

    ktp_controller.networking.ipset.create_ipset("myset", 30)

    check_call_mock.assert_called_once_with(
        ["ipset", "create", "myset", "hash:ip", "timeout", "30"]
    )


def test_destroy_ipset_invokes_ipset_destroy(mocker):
    check_call_mock = mocker.patch(
        "ktp_controller.networking.ipset.subprocess.check_call", return_value=None
    )

    ktp_controller.networking.ipset.destroy_ipset("myset")

    check_call_mock.assert_called_once_with(["ipset", "destroy", "myset"])


def test_list_ipset_entries_parses_members_with_timeout(mocker):
    output = b"""\
Name: myset
Type: hash:ip
Revision: 7
Header: family inet hashsize 1024 maxelem 65536 timeout 30
Size in memory: 448
References: 0
Number of entries: 2
Members:
192.168.1.5 timeout 7
192.168.1.10 timeout 3
"""
    mocker.patch(
        "ktp_controller.networking.ipset.subprocess.check_output",
        return_value=output,
    )

    entries = ktp_controller.networking.ipset.list_ipset_entries("myset")

    assert entries == [("192.168.1.5", 7), ("192.168.1.10", 3)]


def test_list_ipset_entries_returns_empty_list_for_empty_set(mocker):
    output = b"""\
Name: myset
Type: hash:ip
Revision: 7
Header: family inet hashsize 1024 maxelem 65536 timeout 30
Size in memory: 448
References: 0
Number of entries: 0
Members:
"""
    mocker.patch(
        "ktp_controller.networking.ipset.subprocess.check_output",
        return_value=output,
    )

    entries = ktp_controller.networking.ipset.list_ipset_entries("myset")

    assert entries == []


def test_add_ipset_entry_invokes_ipset_add(mocker):
    check_call_mock = mocker.patch(
        "ktp_controller.networking.ipset.subprocess.check_call", return_value=None
    )

    ktp_controller.networking.ipset.add_ipset_entry("myset", "192.168.1.5", 7)

    check_call_mock.assert_called_once_with(
        ["ipset", "add", "myset", "192.168.1.5", "timeout", "7"]
    )


def test_remove_ipset_entry_invokes_ipset_del(mocker):
    check_call_mock = mocker.patch(
        "ktp_controller.networking.ipset.subprocess.check_call", return_value=None
    )

    ktp_controller.networking.ipset.remove_ipset_entry("myset", "192.168.1.5")

    check_call_mock.assert_called_once_with(["ipset", "del", "myset", "192.168.1.5"])
