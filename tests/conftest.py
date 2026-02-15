# Third-party imports
import pytest

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
