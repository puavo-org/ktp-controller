# Internal imports
from utils import client, testdb, db_engine
from ktp_controller.models import Thing


# Each test function executes in a separate session, each session
# starts with an empty database.


def test_upsert_thing(client):
    response = client.post("/api/v1/thing", json={"name": "thing1", "size": 4})
    assert response.status_code == 200
    assert response.json() == {"name": "thing1", "size": 4}

    response = client.post("/api/v1/thing", json={"name": "thing1", "size": 5})
    assert response.status_code == 200
    assert response.json() == {"name": "thing1", "size": 5}


def test_get_all_things(client, testdb):
    response = client.get("/api/v1/thing")
    assert response.status_code == 200
    assert response.json() == []

    thing1 = Thing(name="thing1", size=3)
    testdb.add(thing1)
    testdb.commit()

    response = client.get("/api/v1/thing")
    assert response.status_code == 200
    assert response.json() == [{"name": "thing1", "size": 3}]

    thing2 = Thing(name="thing2", size=20)
    testdb.add(thing2)
    testdb.commit()

    response = client.get("/api/v1/thing")
    assert response.status_code == 200
    assert response.json() == [
        {"name": "thing1", "size": 3},
        {"name": "thing2", "size": 20},
    ]


def test_get_existing_thing(client, testdb):
    new_thing = Thing(name="existing_thing", size=5)
    testdb.add(new_thing)
    testdb.commit()

    response = client.get("/api/v1/thing/existing_thing")
    assert response.status_code == 200
    assert response.json() == {"name": "existing_thing", "size": 5}


def test_get_non_existing_thing(client):
    response = client.get("/api/v1/thing/non_existing")
    assert response.status_code == 404
    assert response.json() == {"detail": "Thing 'non_existing' does not exist"}
