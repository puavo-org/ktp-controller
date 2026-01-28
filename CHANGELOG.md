# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased]

### Added

- Non-final answer files are periodically transferred from Abitti2 to Exam-O-Matic.
- Direct personal identifiers are removed from all Abitti2 stats messages on receipt.
- Services are now automatically restarted on failure.
- `LICENSE` file is now included in release files.
- `CHANGELOG.md` file now included in release files.
- Added new environment variable `KTP_CONTROLLER_EXAMOMATIC_PING_INTERVAL_SEC` to allow overriding default (30s) ping interval.
- Added new environment variable `KTP_CONTROLLER_ANSWER_TRANSFER_INTERVAL_SEC` to allow overriding default (300s) answer transfer interval.

### Changed

- Logging messages are improved.
- Timeouts of HTTP requests to Exam-O-Matic are increased to make connections more resilient.


## [0.1.2] - 2025-01-18

This is the first real release.

### Fixed

- version number in `pyproject.toml`


## [0.1.1] - 2025-01-18 [YANKED]

Yanked because of invalid version number.

### Fixed

- shebangs in bundle


## [0.1.0] - 2025-01-18 [YANKED]

Yanked because all scripts had broken shebangs.

### Added

- initial release
