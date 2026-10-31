import ktp_controller.os


def test_get_puavo_os_image_name_returns_first_line_of_name_file(mocker):
    readfirstline_mock = mocker.patch(
        "ktp_controller.utils.readfirstline", return_value="O2611"
    )

    assert ktp_controller.os.get_puavo_os_image_name() == "O2611"
    readfirstline_mock.assert_called_once_with("/etc/puavo-image/name")


def test_get_puavo_os_image_name_returns_none_on_any_error(mocker):
    mocker.patch("ktp_controller.utils.readfirstline", side_effect=FileNotFoundError())

    assert ktp_controller.os.get_puavo_os_image_name() is None


def test_get_puavo_os_image_release_returns_first_line_of_release_file(mocker):
    readfirstline_mock = mocker.patch(
        "ktp_controller.utils.readfirstline", return_value="O2611 Broom"
    )

    assert ktp_controller.os.get_puavo_os_image_release() == "O2611 Broom"
    readfirstline_mock.assert_called_once_with("/etc/puavo-image/release")


def test_get_puavo_os_image_release_returns_none_on_any_error(mocker):
    mocker.patch("ktp_controller.utils.readfirstline", side_effect=FileNotFoundError())

    assert ktp_controller.os.get_puavo_os_image_release() is None
