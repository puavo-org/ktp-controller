# Standard library imports
import dataclasses

# Third-party imports
import pytest

# Internal imports
import ktp_controller.schemas

# Relative imports
from .bot import Abitti2Student
from .utils import browser_chrome
from .utils import browser_firefox


@pytest.fixture(scope="session")
def student1(browser_firefox):
    yield Abitti2Student(browser_firefox)


@pytest.fixture(scope="session")
def student2(browser_chrome):
    yield Abitti2Student(browser_chrome)


@dataclasses.dataclass
class _TestRunState:
    scheduled_exam_package1: dict | None = None
    scheduled_exam_package2: dict | None = None
    student_access_code: ktp_controller.schemas.StudentAccessCode | None = None


@pytest.fixture(scope="session")
def testrunstate():
    yield _TestRunState()
