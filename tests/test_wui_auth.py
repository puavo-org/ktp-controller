import pytest

import ktp_controller.wui.auth as auth


def _status_report(username="invigilator1", passphrase="s3cret"):
    return {
        "abitti2": {
            "supervisor_username": username,
            "supervisor_passphrase": passphrase,
        }
    }


@pytest.mark.anyio
async def test_authenticate_accepts_matching_credentials(mocker):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=_status_report(),
    )

    assert await auth.authenticate("invigilator1", "s3cret") is True


@pytest.mark.anyio
async def test_authenticate_rejects_wrong_password(mocker):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=_status_report(),
    )

    assert await auth.authenticate("invigilator1", "wrong") is False


@pytest.mark.anyio
async def test_authenticate_rejects_wrong_username(mocker):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=_status_report(),
    )

    assert await auth.authenticate("someoneelse", "s3cret") is False


@pytest.mark.anyio
async def test_authenticate_raises_when_passphrase_unavailable(mocker):
    mocker.patch(
        "ktp_controller.api.client.get_last_status_report",
        return_value=None,
    )

    with pytest.raises(RuntimeError):
        await auth.authenticate("invigilator1", "s3cret")


@pytest.mark.anyio
async def test_session_store_roundtrip():
    session_id = await auth._SESSION_STORE.create(
        {"username": "alice", "permissions": ["wui.invigilator.view"]}
    )
    try:
        data = await auth._SESSION_STORE.get(session_id)
        assert data == {"username": "alice", "permissions": ["wui.invigilator.view"]}

        await auth._SESSION_STORE.touch(session_id)
        assert await auth._SESSION_STORE.get(session_id) is not None
    finally:
        await auth._SESSION_STORE.delete(session_id)

    assert await auth._SESSION_STORE.get(session_id) is None


@pytest.mark.anyio
async def test_create_session_stores_permissions_from_api(mocker):
    mocker.patch(
        "ktp_controller.api.client.get_or_create_user_permissions",
        return_value=["wui.invigilator.view"],
    )

    session_id = await auth.create_session("alice")
    try:
        data = await auth._SESSION_STORE.get(session_id)
        assert data == {"username": "alice", "permissions": ["wui.invigilator.view"]}
    finally:
        await auth.destroy_session(session_id)
