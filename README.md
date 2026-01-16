# ktp-controller

[![Makefile CI](https://github.com/opinsys/ktp-controller/actions/workflows/makefile.yml/badge.svg)](https://github.com/opinsys/ktp-controller/actions/workflows/makefile.yml)

Connection diagram:

```
                            :                   +-------+
                   Internet : Device            |  CLI  |
                            :                   +-o-----+
                            :                     | |
                            :                  WS | | HTTP
                            :                     | v
                            :                   +-o-----+
                            :                   |       |
                            :                   |  API  |
                            :                   |       |
                            :                   +-------+
+-----------------------+   :                     o ^                      +---------+
|      Exam-O-Matic     |<------(HTTPS)---+       | |       +--(HTTPS)---->| Abitti2 |
+-----------------------+   :             |    WS | | HTTP  |              +---------+
                      o     :             |       o |       |                  o
                      |     :             +-----+-------+---+                  |
                      |     :                   |       |                      |
                      +---------(WSS)----------o| Agent |o--------(WSS)--------+
                            :                   |       |
                            :                   +-------+
```

KTP Controller consists of two main components:
- Agent
- API

Agent communicates with all components (Exam-O-Matic, Abitti2 and API)
and is responsible for making them play well together. It uses API to
store necessary data in a persistent database storage.

The API application is built on FastAPI (https://fastapi.tiangolo.com/).

Dependencies of this project are managed with UV (https://github.com/astral-sh/uv).

The database access is abstracted with SQLAlchemy (https://www.sqlalchemy.org/).

Database migrations are handled by Alembic (https://alembic.sqlalchemy.org/en/latest/).

Processes are launched and kept running with Supervisor (https://supervisord.org/).

## Development

Install uv:

```
make uv-install
```

This installs uv to `~/.local/bin`.

All other packages are installed BY uv to a separate virtual env.

### Update dependencies

To update the virtual environment with new releases of all
dependencies, and to record the set of packages to `uv.lock`, run:

```
make dev-update
```

If the set of packages is ok, remember to commit the lock file:

```
git commit uv.lock -m 'Update dependencies'
```
