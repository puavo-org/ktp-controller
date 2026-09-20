import ktp_controller.api.models as models


def test_get_or_create_user_permissions_creates_user_with_default_role(client, testdb):
    response = client.post(
        "/api/v1/user/get_or_create_user_permissions",
        json={"username": "alice"},
    )

    assert response.status_code == 200
    assert response.json() == ["wui.invigilator.view"]

    db_user = testdb.query(models.User).filter_by(username="alice").one()
    assert [role.name for role in db_user.roles] == ["invigilator"]


def test_get_or_create_user_permissions_is_idempotent(client, testdb):
    for _ in range(2):
        response = client.post(
            "/api/v1/user/get_or_create_user_permissions",
            json={"username": "bob"},
        )
        assert response.status_code == 200

    assert testdb.query(models.User).filter_by(username="bob").count() == 1


def test_get_or_create_user_permissions_returns_no_permissions_without_role(
    client, testdb
):
    testdb.add(models.User(dbid=None, username="norole", roles=[]))
    testdb.commit()

    response = client.post(
        "/api/v1/user/get_or_create_user_permissions",
        json={"username": "norole"},
    )

    assert response.status_code == 200
    assert response.json() == []
