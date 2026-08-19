# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [UNRELEASED]

### Added

- In Puavo OS, `/opt/ktp-controller/ktp-controller bash` subcommand is back!


## [0.6.0] - 2026-08-09

### Added

- A new no-op endpoint (GET /api/v1/system/echo) which is safe to be
  called anytime. Can be used for testing purposes.

- Periodic cleanup of:

  - cached raw scheduling info requests: raw scheduling info requests
    received from Exam-O-Matic are now retained only for 14
    days. Previously, they were stored for an eternity. An eternity is
    a a long time and bloats the database unnecessarily. 14 days is a
    good compromise and is inline with local data retention in
    general.

  - log files older than 14 days (last modified more than 14 days
    ago).

  - cached exam files older than 30 days (last modified more than 30
    days ago). Last modified timestamps of cached exam files are also
    updated when KTP Controller would download them (cache-hit).
  
  - all empty directories below `~/.local/share/ktp-controller`.
  
  - all archived dirs, not just archived exam package dirs.

### Changed

- In Puavo OS, all logs are sent to syslog.

- Archived exam packages and archived answers are NOT included in
  status reports (in `cached_files`) anymore.
  
- Removed redundant internal HTTP requests and started to cache
  Abitti2 server version.

- All dependencies have been updated.

- Upload answers files to Exam-O-Matic in newest-answers-first order.

- Non-uploaded intermediate (non-final) answers files are just
  archived and not uploaded after the final answers file is uploaded
  to Exam-O-Matic successfully. However, all intermediate answers
  files are still retained locally for two weeks.
  

### Fixed

- Abitti2: use `POST /api/end-student-exam` instead of deprecated
  `POST /api/end-student-session`.

- Periodic cleanup of archived exam package files.

- Loggers are now named after their module (`__name__`) instead of the
  source file path (`__file__`), producing readable logger names.

- Manual exam package commands (prepare/start/stop/archive) now report
  `ok` instead of always reporting `ok_no_change`, even when they did
  change the state of the current exam package.

### Removed

- Orphan answers files (answers of manually started exams) are not
  saved anymore.


## [0.5.7] - 2026-06-03

### Fixed

- KTP Controller Agent is restarted and fully re-initialized if any of
  it's websocket maintenance task aborts unexpectedly.

- Ensure answers files are always uploaded in ascending timestamp
  order, i.e. oldest first.

- Final answers are downloaded from Abitti2 just once.

### Changed

- Answers file uploading is now completely independent task. Any
  failure in the final answers file upload does not prevent the next
  scheduled exam package to start anymore.

- Status reports are sent to Exam-O-Matic at most once per 30 secs.


## [0.5.6] - 2026-05-12

### Fixed

- Fixed Github build environment again.


## [0.5.5] - 2026-05-12

### Fixed

- Fixed Github build environment.


## [0.5.4] - 2026-05-12

### Fixed

- Now, build bundle files include all necessary libraries for running
  with Python 3.11.2. Previously, bundle file was built targeting
  3.11.14, which caused some of the required libs (at least
  async_timeout) to be missing from the bundle.


## [0.5.3] - 2026-05-11

### Fixed

- Version number in an internal version file.


## [0.5.2] - 2026-05-11

### Fixed

- Fixed the handling of task cancellations. Now various asynchronous
  tasks conducted by the Agent component of KTP Controller do not just
  silently stop. Should a task get cancelled unexpectedly, for what
  ever reason (network, explosion, aliens, etc.), a message is logged
  and necessary actions are taken to return to normal operation.


## [0.5.1] - 2026-05-06

### Fixed

- Periodic exam refresh task is now kept alive (and errors logged), no
  matter what happens during exam refresh.


## [0.5.0] - 2026-05-04

### Added

- All Abitti2-related code and functionality imported from Puavo OS.

### Changed

- All dependencies have been updated.


## [0.4.7] - 2026-06-03

## Fixed

- KTP Controller Agent is restarted and fully re-initialized if any of
  it's websocket maintenance task aborts unexpectedly.


## [0.4.6] - 2026-05-25

## Fixed

- Ensure answers files are always uploaded in ascending timestamp
  order, i.e. oldest first.


## [0.4.5] - 2026-05-24

### Changed

- Answers file uploading is now completely independent task. Any
  failure in the final answers file upload does not prevent the next
  scheduled exam package to start anymore.

- Status reports are sent to Exam-O-Matic at most once per 30 secs.

## Fixed

- Final answers are downloaded from Abitti2 just once.


## [0.4.4] - 2026-05-11

### Fixed

- Fixed the handling of task cancellations. Now various asynchronous
  tasks conducted by the Agent component of KTP Controller do not just
  silently stop. Should a task get cancelled unexpectedly, for what
  ever reason (network, explosion, aliens, etc.), a message is logged
  and necessary actions are taken to return to normal operation.


## [0.4.3] - 2026-05-06

### Fixed

- Periodic exam refresh task is now kept alive (and errors logged), no
  matter what happens during exam refresh.


## [0.4.2] - 2026-04-29

### Fixed

- Abitti2 students waiting for authorization are considered inactive
  and no longer block exam package state transitions.

### Changed

- Duplicate exam files (based on SHA256) are no longer included in
  exam package files, as Abitti2 fails to process them. Should
  Exam-O-Matic ever produce scheduled exam package definitions with
  duplicate exam files, rest assured that KTP Controller will filter
  them out of the final package (and log a warning message).


## [0.4.1] - 2026-04-16

### Fixed

- Resolved an issue where invalid Abitti2 exam decryption codes
  triggered unnecessary error logging, ensuring the process continues
  smoothly as long as all necessary exams are successfully decrypted.


## [0.4.0] - 2026-04-12

### Fixed

- Fixed the root cause of benign supervisor event buffer overflow
  errors to prevent confusion.

### Changed

- Cleanup old answers files (more than 2 weeks old) and old archived
  exam packages (exam packages marked as archived and more than 1 day
  old).

- All HTTP(S) requests are now made asynchronously using httpx.

- All dependencies have been updated.

### Added

- Add configuration option to control automatic student access code
  change:

  `KTP_CONTROLLER_ABITTI2_CHANGE_STUDENT_ACCESS_CODE_AUTOMATICALLY=true|false`

  The default remains unchanged and is `true`.

- In PuavoOS, `~/ktp-jako` (created if not exist) contains now symbolic links to:
  - logs
  - exam-files
  - exam-packages
  - answers-files
  - orphan-answers-files



## [0.3.13] - 2026-04-16

### Fixed

- Resolved an issue where invalid Abitti2 exam decryption codes
  triggered unnecessary error logging, ensuring the process continues
  smoothly as long as all necessary exams are successfully decrypted.


## [0.3.12] - 2026-04-10

### Fixed

- Allow abitti2server to exit with status code 0.


## [0.3.11] - 2026-04-09

### Fixed

- Refresh exams independently of Exam-O-Matic websocket pongs:
  websocket connections to Exam-O-Matic seem unreliable for an unknown
  reason. Having independent asynchronous periodic (once per 3min)
  refresh task ensures exam info gets refreshed even if websocket
  connection is down.


## [0.3.10] - 2026-04-07

### Fixed

- Send intermediate answers to Exam-O-Matic as is_final=FALSE (was is_final=UNKNOWN).


## [0.3.9] - 2026-03-31

### Fixed

- Obtain version information from Abitti2 v1.26.0+ correctly.


## [0.3.8] - 2026-03-25

### Fixed

- Offload possibly long running answer transfers to background
  threads. This avoids blocking the main loop for extended periods of
  time. Which in turn means that websockets can keep playing their
  keepalive ping-pong game behind the scenes.

### Changed

- Periodic answer transfer task is now running only when exam package
  is `running`. Previously, it was running also when exam packages
  were `stopping`, but that does not make much sense; the final answer
  transfer is about to get started anyways, when the exam package is
  completely `stopped`.


## [0.3.7] - 2026-03-24

### Fixed

- Agent now logs errors that occurred during periodic answer transfers.

- Periodic answer transfer task is not re-started anymore when the
  scheduled exam package is stopped. This caused issues when periodic
  answer transfer itself was failing (for any reason). Final archival
  process will take care of transferring final answers from Abitti2 to
  Exam-O-Matic when the exam package has been stopped.


## [0.3.6] - 2026-03-23

### Changed

- Answers file download timeout (from Abitti2) increased from 5sec to 200secs (connect timeout 6.1sec)
- Answers file upload timeout (to Exam-O-Matic) increased from 60secs to 600secs (connect timeout 6.1sec)
- Exam package upload timeout (to Abitti2) increased from 20secs to 60secs (connect timeout 6.1sec)


## [0.3.5] - 2026-03-22

### Fixed

- Fix regression: change to the uploading and decrypting logic in
  v0.3.3 caused agent to upload just the very first exam package,
  which effectively limited exam package scheduling to only run once per
  session.

- Ensure to not flood Abitti2 with reset requests.

- Orphan answers are not saved from waiting lobby exam.


## [0.3.4] - 2026-03-18

### Fixed

- agent: logging statement in preparation phase


## [0.3.3] - 2026-03-18

### Fixed

- agent: upload current exam package, decrypt it and change access
  codes as the first steps. The current exam package is ready when
  these steps are finished.


## [0.3.2] - 2026-03-17

### Changed

- `cli status` does not show cached files anymore, by default. Use `--show-cached-files` to include them in the output.
- The logging level of `cli` is now WARNING by default to not pollute the output unnecessarily.
- All `*_at` timestamps in `cli status` output have also human-friendly ago postpositions / suffixes, e.g. (1h 34m 2s ago).

### Fixed

- api: error handling in websocket pubsub broadcasting
  - error in a single websocket does not bring the whole broadcaster down anymore


## [0.3.1] - 2026-03-09

### Added

- `ktp-controller bash` accepts extra arguments
  - i.e. it can be run like so: `ktp-controller bash -c 'ls'`

### Fixed

- agent: avoid respawning too fast
- supervisor: restart critical services (practically unlimited number of times)


## [0.3.0] - 2026-03-08

### Added

- [New status report format](ktp_controller/examomatic/schemas.py#L50)
  - [Example1](docs/status_report_v1_example1.json)
  - [Example2](docs/status_report_v1_example2.json)
  - [Example3](docs/status_report_v1_example3.json)
  - [Example4](docs/status_report_v1_example4.json)
  - [Example5](docs/status_report_v1_example5.json)
  - [Example6](docs/status_report_v1_example6.json)
  - [Example7](docs/status_report_v1_example7.json)
- All status reports are validated before sending.
- Asynchronous tasks are cleaned up properly.
- Signal handling and robust asynchronous task cleanup
- All command line programs have now `--version` option.
- Added new environment variable `KTP_CONTROLLER_ABITTI2_ALLOW_STUDENTS_TO_USE_BROWSERS` to allow overriding the default behavior.
- Puavo OS: `puavo-ers-naksu2` and `puavo-ers-abitti2server` are now part of the supervised run.
- Improved system resilience by automatically attempting to reconnect to Redis during connection failures.
- Single Redis client connection for all websocket connections (agent and UI).
- Added local backup for orphan answer files; in auto-control mode, answers from unknown exams (not launched by KTP Controller) are now saved locally before proceeding.
- Mark all uploaded answers with `.archived` sentinel file.
- More robust error handling.
- The definition of "active" student is revised:
  - If student.isConnected is False, then the student is inactive
  - If student.updateTime is older than 30mins, then the student is inactive
  - If student.examFinished, then the student is inactive
  - If student.sessionStatus is 'session_ended', then the student is inactive
  - If student.sessionStatus starts with 'exam_finished_by_', then student is inactive
  - Otherwise student is active

### Removed

- Support for legacy status report format is removed.

### Changed

- Logging verbosity is reduced.
- Log files are preserved from every run.
- React faster to Abitti2 state changes.
- By default, do not allow students to use browsers.

### Fixed

- Agent and API sub-components are guaranteed to get restarted should they crash for any reason.
- API does not run out of open files anymore (previously leaked Redis client sockets in some error conditions).
- Abitti2 is asked to encrypt exams when exam package is started, not when exam package is locked.
  - This ensures students cannot access exams with old codes.


## [0.2.3] - 2026-02-24

### Fixed

- API does not run out of open files anymore (previously leaked Redis client sockets in some error conditions).

### Changed

- Improved system resilience by automatically attempting to reconnect to Redis during connection failures, preserving subscribed websockets.
- Use single Redis client connection for all websocket connections (agent and UI).
- Added local backup for orphan answer files; in auto-control mode, answers from unknown exams (not launched by KTP Controller) are now saved locally before proceeding.
- Mark all uploaded answers with `.archived` sentinel file.
- More robust error handling.


## [0.2.2] - 2026-02-24

### Fixed

- Guarantee that continuous non-final answer transfer task is always
  running when exam package is `stopping` or `stopped`. Fix in the
  version 0.2.1 was not enough, because it only ensured the task was
  running when exam package was `running`.

- Reduce noise from logs.

- Deal with situations where the very first status report is not yet
  produced.


## [0.2.1] - 2026-02-11

### Fixed

- Guarantee that continuous non-final answer transfer task is always running when exam package is running.


## [0.2.0] - 2026-02-03

### Added

- Exams are not stopped until all students have finished or the next exam is about to start.
- Abitti2 server domain is now included in status reports sent to Exam-O-Matic.
- Non-final answers files are periodically transferred from Abitti2 to Exam-O-Matic.
- Direct personal identifiers are removed from all Abitti2 stats messages on receipt.
- Services are now automatically restarted on failure.
- `LICENSE` file is now included in release files.
- `CHANGELOG.md` file is now included in release files.
- Added new environment variable `KTP_CONTROLLER_EXAMOMATIC_PING_INTERVAL_SEC` to allow overriding default (30s) ping interval.
- Added new environment variable `KTP_CONTROLLER_ANSWER_TRANSFER_INTERVAL_SEC` to allow overriding default (300s) answer transfer interval.

### Changed

- Timeouts of HTTP requests to Exam-O-Matic are increased to make connections more resilient.


## [0.1.2] - 2026-01-18

This is the first real release.

### Fixed

- version number in `pyproject.toml`


## [0.1.1] - 2026-01-18 [YANKED]

Yanked because of invalid version number.

### Fixed

- shebangs in bundle


## [0.1.0] - 2026-01-18 [YANKED]

Yanked because all scripts had broken shebangs.

### Added

- initial release
