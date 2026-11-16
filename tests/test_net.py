import ktp_controller.net


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
