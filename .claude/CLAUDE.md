# Architecture

- See @README.md for project overview.


## Component: API

@ktp_controller/api/

Key technology: Python3, FastAPI, Uvicorn, SQLAlchemy, Sqlite3, Alembic, Redis

### Main responsibilities

- Permanent data storage for Agent-driven state machine.
- Async command dispatching to Agent via websockets.


## Component: Agent

@ktp_controller/agent/

Key technology: Python3, asyncio

### Main responsibilities

- Control Abitti2 (external web service) based on the information
  received from Exam-O-Matic (another external web service).

- Execute commands received from API via websockets.

- Deliver status reports back to Exam-O-Matic.


# Git instructions

- Do not sign commits.
- Always ensure `make check` and `make test` succeeds before committing.
- Prefer many smaller logical commits than one massive.


# Summary instructions

When using compact, focus on:

- Recent code changes.
- Test results.
- Architecture decisions made in this session.
