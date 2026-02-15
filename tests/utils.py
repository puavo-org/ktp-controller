# Standard library imports
import datetime
import enum
import random
import sys
import time

# Third-party imports

# Internal imports
import ktp_controller.examomatic.client
import ktp_controller.utils


def assert_response(response, *, expected_status_code: int):
    try:
        assert response.status_code == expected_status_code
    except AssertionError:
        print(response.content, file=sys.stderr)
        raise


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
    if birthday.year < 1900:
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


def assert_odotusaulakoe_is_running(timeout: int = 30):
    odotusaulakoe_is_running = False
    for i in range(timeout):
        state = ktp_controller.examomatic.client._post("/mock/get_state").json()
        status_reports = state["status_reports"]
        started_exam_titles = [
            e["title"]
            for e in status_reports[-1]["abitti2"]["exams"]
            if e["started_at"] is not None
        ]
        if len(started_exam_titles) > 0:
            if "Odotusaulakoe" in started_exam_titles:
                odotusaulakoe_is_running = True
                break
        time.sleep(1)
    assert odotusaulakoe_is_running


def assert_status_report_is_fresh(status_report, max_age_secs: int = 30) -> bool:
    return (
        ktp_controller.utils.utcnow()
        - datetime.datetime.fromisoformat(status_report["created_at"])
    ).total_seconds() <= max_age_secs
