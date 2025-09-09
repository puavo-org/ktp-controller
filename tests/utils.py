# Third-party imports
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import fastapi.testclient
import pytest

# Internal imports
from ktp_controller.api.main import APP
from ktp_controller.api.database import get_db
from ktp_controller.api.models import Base, Thing


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def testdb(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    db = sessionmaker(autocommit=False, autoflush=False, bind=connection)()
    yield db
    db.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(testdb):
    def override_get_db():
        try:
            yield testdb
        finally:
            testdb.close()

    APP.dependency_overrides[get_db] = override_get_db
    yield fastapi.testclient.TestClient(APP)
    APP.dependency_overrides.clear()
