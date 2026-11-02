import pytest

import ktp_controller.os

_FUNCS = [
    pytest.param(
        ktp_controller.os.get_puavo_os_image_name,
        "/etc/puavo-image/name",
        "O2611",
        id="image_name",
    ),
    pytest.param(
        ktp_controller.os.get_puavo_os_image_release,
        "/etc/puavo-image/release",
        "O2611 Broom",
        id="image_release",
    ),
]


@pytest.mark.parametrize(("func", "expected_path", "raw_value"), _FUNCS)
def test_get_puavo_os_image_info_returns_first_line_of_file(
    mocker, func, expected_path, raw_value
):
    readfirstline_mock = mocker.patch(
        "ktp_controller.utils.readfirstline", return_value=raw_value
    )

    assert func() == raw_value
    readfirstline_mock.assert_called_once_with(expected_path)


@pytest.mark.parametrize(("func", "expected_path", "raw_value"), _FUNCS)
def test_get_puavo_os_image_info_returns_none_on_any_error(
    mocker, func, expected_path, raw_value
):
    mocker.patch("ktp_controller.utils.readfirstline", side_effect=FileNotFoundError())

    assert func() is None
