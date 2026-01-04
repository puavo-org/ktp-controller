# Standard library imports
import datetime
import enum
import random
import sys

# Third-party imports
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import fastapi.testclient
import pytest
import selenium.webdriver

# Internal imports
from ktp_controller.api.main import APP
from ktp_controller.api.database import get_db
from ktp_controller.api.models import Base


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def testdb(db_engine):  # pylint: disable=redefined-outer-name # Fixture usage
    connection = db_engine.connect()
    transaction = connection.begin()
    db = sessionmaker(autocommit=False, autoflush=False, bind=connection)()
    yield db
    db.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(testdb):  # pylint: disable=redefined-outer-name # Fixture usage
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
    yield datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)


def assert_response(response, *, expected_status_code: int):
    try:
        assert response.status_code == expected_status_code
    except AssertionError:
        print(response.content, file=sys.stderr)
        raise


@pytest.fixture
def browser_chrome():
    chrome = selenium.webdriver.Chrome()
    try:
        chrome.maximize_window()
        yield chrome
    finally:
        chrome.quit()


@pytest.fixture
def browser_firefox():
    firefox = selenium.webdriver.Firefox()
    try:
        firefox.maximize_window()
        yield firefox
    finally:
        firefox.quit()


class Gender(str, enum.Enum):
    FEMALE = "female"
    MALE = "male"


HETU_CHECK_CHARS = "0123456789ABCDEFHJKLMNPRSTUVWXY"


# https://en.wikipedia.org/wiki/National_identification_number#Finland
# https://www.tuomas.salste.net/doc/tunnus/henkilotunnus.html#keinotunnus
def random_artificial_hetu(gender: Gender | None = None):
    if gender is None:
        range_step = 1  # Whole zzz value space is used.
    else:
        Gender(gender)
        range_step = 2  # Only half of the zzz value space is used.

    zzz = random.randrange(901 if gender == Gender.MALE else 900, 1000, range_step)

    now_date = datetime.datetime.now().date()

    # By default, we want to generate artificial hetus for
    # reasonable young testers, because they are assumed to be
    # Abitti2 students.
    min_birthday = now_date - datetime.timedelta(days=18 * 365)
    max_birthday = now_date - datetime.timedelta(days=7 * 365)

    birthday = min_birthday + datetime.timedelta(
        days=random.randrange(0, (max_birthday - min_birthday).days)
    )

    if birthday.year < 1800:
        raise RuntimeError("mummys cannot have hetus")
    elif birthday.year < 1900:
        c = "+"  # They are all dead.
    elif birthday.year < 2000:
        c = "-"
    elif birthday.year < 2100:
        c = "A"
    else:
        raise RuntimeError("future is here")

    ddmmyy = birthday.strftime("%d%m%y")

    q = HETU_CHECK_CHARS[int(f"{ddmmyy}{zzz}") % 31]

    return f"{ddmmyy}{c}{zzz}{q}"
