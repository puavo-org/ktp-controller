# Standard library imports
import datetime
import time

# Third-party imports


# Internal imports
import ktp_controller.abitti2.client
import ktp_controller.api.client
import ktp_controller.examomatic.client

from .utils import browser_chrome
from .bot import Abitti2Student

# Test functions are and must be executed sequentially. In unit tests,
# it's not a good idea to build tests which depend on each other, but
# this is integration test scenario, and pytest is just a neat way to
# run them too. So, each test function is a sequential step in the
# testrun.


def test_student_login(browser_chrome):
    student = Abitti2Student(browser_chrome)
    student.start_exam(
        exam_uuid="390e7988-ff0e-42b4-a2e6-d13a969e7103",
        exam_title="Odotusaulakoe",
        access_code=("1234", "xx"),
    )
