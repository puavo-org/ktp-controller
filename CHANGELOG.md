# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [UNRELEASED]

### Added

- [New status report format](ktp_controller/examomatic/schemas.py#L50)
  - [Example1](docs/status_report_v1_example1.json)
  - [Example2](docs/status_report_v1_example2.json)
  - [Example3](docs/status_report_v1_example3.json)
- Validation of status reports before sending
- Signal handling and robust asynchronous task cleanup
- `--version` option to all command line programs
- Added new environment variable `KTP_CONTROLLER_ABITTI2_ALLOW_STUDENTS_TO_USE_BROWSERS` to allow overriding default (`False`) behavior
- Puavo OS: `puavo-ers-naksu2` and `puavo-ers-abitti2server` are now part of the supervised run

### Removed

- Support for legacy status report format

### Changed

- Less verbose logging by default
- Log files are preserved from every run.
- Faster reaction time to Abitti2 state changes
- By default, do not allow students to use browsers

### Fixed

- Sub-component supervision, i.e. agent and API are guaranteed to get
  restarted should they crash for any reason.


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
