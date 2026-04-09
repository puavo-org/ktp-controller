# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

- Agent now logs errors occured during periodic answer transfers.

- Periodic answer transfer task is not re-started anymore when the
  scheduled exam package is stopped. This caused issues when periodic
  answer transfer itself was failing (for any reason). Final archival
  process will take care of transfering final answers from Abitti2 to
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
  which effectively made exam package scheduling to work only once per
  runtime.

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
- Self-healing capabilities if Redis connection fails, i.e. try reconnecting until Redis is back online.
- Single Redis client connection for all websocket connections (agent and UI).
- Orphan answer files are rescued, i.e. in auto-control mode, if Abitti2 is running an unknown exam (not launched by KTP Controller), save answers locally before proceeding.
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

- Self-heal wounds caused by Redis connection failures, i.e. try reconnecting until Redis is back online and preserve subscribed websockets.
- Use single Redis client connection for all websocket connections (agent and UI).
- Orphan answer files are rescued, i.e. in auto-control mode, if Abitti2 is running an unknown exam (not launched by KTP Controller), save answers locally before proceeding.
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
- Non-final answer files are periodically transferred from Abitti2 to Exam-O-Matic.
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
