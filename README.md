# ktp-controller

```
                                                +-------+
                                                |  UI   |
                                                +-------+
                                                    |
                                                    | HTTP
                                                    v
+-----------------------+                       +-------+                +------------------+
| Exam-O-Matic listener |---------(HTTP)------->|       |<-----(HTTP)----| Abitti2 listener |
+-----------------------+                       |       |                +------------------+
            o                                   |  API  |                       o
            |                                   |       |                       |
            | WSS                               |       |                       |
-.-.-.-.-.-.|-.-.-.-.-.--.-.+                   |       |                   WSS |
            o               :                   |       |                       o
+-----------------------+   :                   +-------+                  +---------+
|      Exam-O-Matic     |<---------(HTTPS)-----/    ^     \----(HTTPS)---->| Abitti2 |
+-----------------------+   :                       |                      +---------+
                            :                       | HTTP
                   Internet : Device            +-------+
                            :                   | Agent |
                            :                   +-------+
```

KTP Controller consists of three components:
- API
- Abitti2 listener
- Exam-O-Matic listener

Abitti2 listener is responsible for maintaining a websocket to
Abitti2, listening to it, and delivering events, sent by Abitti2, to
the API app.

Exam-O-Matic listener is to Exam-O-Matic what Abitti2 listener is to
Abitti2; it is responsible for maintaining a websocket to
Exam-O-Matic, listening to it, and delivering events to the API app.

The API application is built on FastAPI (https://fastapi.tiangolo.com/).

Dependencies of this project are managed with Poetry (https://python-poetry.org/).

The database access is abstracted with SQLAlchemy (https://www.sqlalchemy.org/).

Database migrations are handled by Alembic (https://alembic.sqlalchemy.org/en/latest/).

Processes are launched and kept running with Supervisor (https://supervisord.org/).

## Development

Install poetry from APT repositories:

```
apt install python3-poetry
```

or install the latest from PyPI:

```
pip3 install --user --break-system-packages poetry # For some strange reason, you need --break-system-packages eventhough you are installing to user's homedir.
```

This installs poetry to `~/.local/bin` so ensure it's in your PATH.

After installing poetry, everything you need for development is one make command aways

### Create new development environment

To create a new virtual environment and install all the required packages into it, run:

```
make dev-install
```

### Run in development mode

Run API app:

```
make dev-run-api
```

Interactive API documentation: http://127.0.0.1:8000/docs

Run Exam-O-Matic listener:

```
make dev-run-examomatic-listener
```

Run Abitti2 listener:

```
make dev-run-abitti2-listener
```


### Update dependencies

To update the virtual environment with new releases of all
dependencies, and to record the set of packages to `poetry.lock`, run:

```
make dev-update
```

If the set of packages is ok, remember to commit the lock file:

```
git commit poetry.lock -m 'poetry update'
```
