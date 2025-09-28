# ktp-controller

Connection diagram:

```
                            :                   +-------+
                   Internet : Device            |  UI   |
                            :                   +-------+
                            :                       |
                            :                       | HTTP
                            :                       v
                            :                   +-------+                                     
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
- DB

Agent communicates with all components (Exam-O-Matic, Abitti2 and API)
and is responsible for making them play well together. It uses API to
store necessary data in a persistent database storage.

The API application is built on FastAPI (https://fastapi.tiangolo.com/).

Dependencies of this project are managed with Poetry (https://python-poetry.org/).

The database access is abstracted with SQLAlchemy (https://www.sqlalchemy.org/).

Database migrations are handled by Alembic (https://alembic.sqlalchemy.org/en/latest/).

Processes are launched and kept running with Supervisor (https://supervisord.org/).

## Development

Install poetry from PyPI:

```
pip3 install --user --break-system-packages poetry # For some strange reason, you need --break-system-packages eventhough you are installing to user's homedir.
```

This installs poetry to `~/.local/bin` so ensure it's in your PATH.

After installing poetry, everything you need for development is one make command away.

### Create new development environment

To create a new virtual environment and install all the required packages into it, run:

```
make dev-install
```

### Run in development mode

Just run:

```
make dev-run
```

Then interactive API documentation: http://127.0.0.1:8000/docs


### Update dependencies

To update the virtual environment with new releases of all
dependencies, and to record the set of packages to `poetry.lock`, run:

```
make dev-update
```

If the set of packages is ok, remember to commit the lock file:

```
git commit poetry.lock -m 'Update dependencies'
```
