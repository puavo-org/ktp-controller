import pytest

import ktp_controller.abitti2.client

_POST = "ktp_controller.abitti2.client._post"

_VALID_CODE = {"keyCode": "8223", "confirmationCode": "cx"}


@pytest.mark.anyio
async def test_change_student_access_code_returns_code_from_immediate_response(
    mocker,
):
    post_mock = mocker.patch(
        _POST,
        return_value=mocker.Mock(
            json=mocker.Mock(return_value={"securityCode": _VALID_CODE})
        ),
    )

    result = await ktp_controller.abitti2.client.change_student_access_code()

    assert result == _VALID_CODE
    post_mock.assert_awaited_once_with("/api/single-security-code")


@pytest.mark.anyio
async def test_change_student_access_code_returns_none_when_deferred(mocker):
    mocker.patch(
        _POST,
        return_value=mocker.Mock(json=mocker.Mock(return_value={})),
    )

    result = await ktp_controller.abitti2.client.change_student_access_code()

    assert result is None


@pytest.mark.anyio
@pytest.mark.parametrize(
    "response_body",
    [
        pytest.param({"securityCode": "not a dict"}, id="not-a-dict"),
        pytest.param(
            {"securityCode": {"keyCode": "8223"}}, id="missing-confirmationCode"
        ),
        pytest.param(
            {"securityCode": {"confirmationCode": "cx"}}, id="missing-keyCode"
        ),
        pytest.param(
            {
                "securityCode": {
                    "keyCode": "8223",
                    "confirmationCode": "cx",
                    "extra": "x",
                }
            },
            id="extra-key",
        ),
        pytest.param(
            {"securityCode": {"keyCode": 8223, "confirmationCode": "cx"}},
            id="keyCode-not-str",
        ),
        pytest.param(
            {"securityCode": {"keyCode": "8223", "confirmationCode": 1}},
            id="confirmationCode-not-str",
        ),
    ],
)
async def test_change_student_access_code_returns_none_for_invalid_security_code(
    mocker, response_body
):
    mocker.patch(
        _POST,
        return_value=mocker.Mock(json=mocker.Mock(return_value=response_body)),
    )

    result = await ktp_controller.abitti2.client.change_student_access_code()

    assert result is None
