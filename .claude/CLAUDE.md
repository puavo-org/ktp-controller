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

### Conventions

- Every `POST /actions/<name>` endpoint (in `ktp_controller/wui/actions/`)
  is gated by its own `wui.actions.<name>` permission, checked via the
  `require_permission` decorator and granted to roles through its own
  Alembic migration (see `alembic/versions/*_add_wui_actions_*`). The
  invigilator template also gets a matching `can_<name>` context flag
  (set in `ktp_controller/wui/invigilator/routes.py`) controlling
  whether the corresponding button/control renders at all.

- Translatable strings (`_()`/`{% trans %}` in Python and `.j2`
  templates) require running `make i18n-extract`, `make i18n-update`,
  and `make i18n-compile` (in that order) to add/refresh the `fi`/`sv`/`en`
  `.po`/`.mo` files before `make check`'s `check-i18n` target will pass.


# Git instructions

- Do not sign commits.
- Always ensure `make check` and `make test` succeeds before committing.
- Prefer many smaller logical commits than one massive.

## Layered commit order for multi-file features

Structure a feature that touches several files/layers as a bottom-up
sequence of commits, each a logical step toward the final solution and
each independently passing `make check`/`make test`:

1. **Capability commits.** Add new capability — library/client
   functions, schema or data-model additions, new enum values, etc. —
   without changing any existing behavior yet. One new
   feature/capability per commit. Dead code (not yet called from
   anywhere) is fine at this stage.
2. **Plumbing commits.** Wire the new capability into the surrounding
   system — dispatch tables, routes, intermediate layers. Split this
   into multiple logically separated commits too, rather than one
   big plumbing commit, where the plumbing has distinct layers of its
   own.
3. **Final connecting commit.** The last step that actually makes the
   feature work end-to-end (e.g. UI wiring, flipping a flag). Since
   everything underneath is already in place, this is normally a small
   diff.
4. **Tests.** Commit test changes separately from the implementation
   they cover, preferably as their own commit(s).


# Summary instructions

When using compact, focus on:

- Recent code changes.
- Test results.
- Architecture decisions made in this session.
