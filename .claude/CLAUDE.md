# Architecture

- See @README.md for project overview.

Multi-process orchestra, managed by supervisord.

`make test` uses @supervisor/test.conf to run unit tests. Execution
takes less than 1min.

`make integration-test` uses @supervisor/integration-test.conf to run
integration tests. Execution takes 20-30mins. During execution, a
testbot launches and uses a browser window on the host.

Running the complete orchestra in production mode requires `sudo` and
is out of your scope.


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


## Component: Web User Interface, WUI

@ktp_controller/wui/

Key technology: Python3, FastAPI, Uvicorn, htmx, Redis

### Main responsibilities

- Provide responsive web UI for exam monitoring and controlling tasks.


# Git instructions

- Do not sign commits.
- Always ensure `make check` and `make test` succeeds before committing.
- Prefer many smaller logical commits than one massive.


# Summary instructions

When using compact, focus on:

- Recent code changes.
- Test results.
- Architecture decisions made in this session.
