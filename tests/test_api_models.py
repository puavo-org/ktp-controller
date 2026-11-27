import datetime

import ktp_controller.api.models as models

# These tests exercise UTCDateTime directly at the SQLAlchemy layer,
# bypassing the HTTP API and Pydantic entirely, to prove the
# normalization to UTC holds no matter where a datetime value comes
# from.


def test_utcdatetime_converts_non_utc_offset_to_utc_instant(testdb):
    non_utc = datetime.datetime(
        2025, 5, 28, 13, 15, tzinfo=datetime.timezone(datetime.timedelta(hours=2))
    )

    testdb.add(
        models.ScheduledExamPackage(
            dbid=None,
            external_id="pkg-non-utc",
            start_time=non_utc,
            end_time=non_utc + datetime.timedelta(minutes=30),
            lock_time=non_utc - datetime.timedelta(minutes=15),
            locked=False,
        )
    )
    testdb.commit()
    testdb.expire_all()

    db_package = (
        testdb.query(models.ScheduledExamPackage)
        .filter_by(external_id="pkg-non-utc")
        .one()
    )

    # Stored values must be the UTC-converted instant, not the
    # wall-clock numbers with the offset silently dropped, and read
    # back as timezone-aware UTC.
    assert db_package.start_time == datetime.datetime(
        2025, 5, 28, 11, 15, tzinfo=datetime.UTC
    )
    assert db_package.end_time == datetime.datetime(
        2025, 5, 28, 11, 45, tzinfo=datetime.UTC
    )
    assert db_package.lock_time == datetime.datetime(
        2025, 5, 28, 11, 0, tzinfo=datetime.UTC
    )
    assert db_package.start_time.tzinfo == datetime.UTC


def test_utcdatetime_treats_naive_value_as_already_utc(testdb):
    naive = datetime.datetime(2025, 5, 28, 11, 15)

    testdb.add(
        models.ScheduledExamPackage(
            dbid=None,
            external_id="pkg-naive",
            start_time=naive,
            end_time=naive + datetime.timedelta(minutes=30),
            lock_time=None,
            locked=False,
        )
    )
    testdb.commit()
    testdb.expire_all()

    db_package = (
        testdb.query(models.ScheduledExamPackage)
        .filter_by(external_id="pkg-naive")
        .one()
    )

    assert db_package.start_time == naive.replace(tzinfo=datetime.UTC)
    assert db_package.lock_time is None


def test_utcdatetime_read_back_values_are_timezone_aware(testdb):
    testdb.add(
        models.ScheduledExamPackage(
            dbid=None,
            external_id="pkg-read",
            start_time=datetime.datetime(2025, 5, 28, 11, 15),
            end_time=datetime.datetime(2025, 5, 28, 11, 45),
            lock_time=None,
            locked=False,
        )
    )
    testdb.commit()
    testdb.expire_all()

    db_package = (
        testdb.query(models.ScheduledExamPackage)
        .filter_by(external_id="pkg-read")
        .one()
    )

    assert db_package.start_time.tzinfo == datetime.UTC
    assert db_package.end_time.tzinfo == datetime.UTC
