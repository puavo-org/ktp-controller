# Standard library imports
import dataclasses
import datetime
import os.path
import shutil

import fastapi.testclient
import pytest
import selenium.webdriver

# Third-party imports
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Internal imports
import ktp_controller.schemas
from ktp_controller.api.database import get_db
from ktp_controller.api.main import APP
from ktp_controller.api.models import Base

# Relative imports
from .bot import Abitti2Student


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
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


@pytest.fixture
def utcnow():
    return datetime.datetime.utcnow().replace(tzinfo=datetime.UTC)


@pytest.fixture(scope="session")
def browser_chrome():
    chrome = selenium.webdriver.Chrome()
    try:
        yield chrome
    finally:
        chrome.quit()


@pytest.fixture(scope="session")
def browser_firefox():
    firefox = selenium.webdriver.Firefox()
    try:
        yield firefox
    finally:
        firefox.quit()


@pytest.fixture(scope="session")
def student1(browser_firefox):
    return Abitti2Student(browser_firefox)


@pytest.fixture(scope="session")
def student2(browser_chrome):
    return Abitti2Student(browser_chrome)


@dataclasses.dataclass
class _TestRunState:
    scheduled_exam_package1: dict | None = None
    scheduled_exam_package2: dict | None = None
    student_access_code: ktp_controller.schemas.StudentAccessCode | None = None


@pytest.fixture(scope="session")
def testrunstate():
    return _TestRunState()


@pytest.fixture
def testdir():
    dirpath = os.path.join(os.path.dirname(__file__), "testdir")
    os.makedirs(dirpath)
    yield dirpath
    shutil.rmtree(dirpath)
