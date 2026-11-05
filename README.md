# KTP Controller

KTP Controller acts as a mediator/agent between two web services:
Exam-O-Matic and Abitti2.

KTP stands for KoeTilaPalvelin, Exam Room Server in English. Hence,
KTP Controller is Exam Room Server Controller. Abitti2 is an
implementation of such server. KTP Controller controls Abitti2 based
on the information it gets from Exam-O-Matic.

Exam-O-Matic (Koejakaja in Finnish) is a webservice which schedules
exams to multiple Exam Room Servers. From KTP Controller's point of
view, Exam-O-Matic is the master data source for exam schedules and
files.

Abitti2 is an exam server, which serves exams as interactive web
content to students. The interactive web content is encoded in exam
files, which are uploaded to Abitti2 as zip bundles, exam file
packages. Abitti2 always deals with exactly one exam file package at a
time, but the exam file package can contain multiple independent exam
files.

Abitti2 exposes HTTP API for uploading exam file packages, decrypting
and starting exams, downloading answers, ending student sessions, etc.

Abitti2 also uses websockets to send status information to attached
listeners.


[![Makefile CI](https://github.com/opinsys/ktp-controller/actions/workflows/makefile.yml/badge.svg)](https://github.com/opinsys/ktp-controller/actions/workflows/makefile.yml)

Typical connection setup:

```
                            :                   +-------+                                :
                   Internet : Device            |  CLI  |                                : LAN
                            :                   +-o-----+                                :
                            :                     | |                                    :
                            :                  WS | | HTTP                               :
                            :                     | v                                    :
                            : +-------+  HTTP   +-o-----+                                :
                            : |       |-------->|       |                                :
                  +---------->|  WUI  |         |  API  |                                :
   HTTPS over VPN |         : |       o---------o       |                                :
                  |         : +-------+   WS    +-o-----+                                :
+-----------------------+   :                     | ^                      +---------+   :
|      Exam-O-Matic     |<------(HTTPS)---+       | |       +--(HTTPS)---->| Abitti2 |<--(HTTPS)-- Student
+---------------------o-+   :             |    WS | | HTTP  |              +---o-----+   :         Browser
       ^              |     :             |       | |       |                  |         :
       |              |     :             +-----+-o-----+---+                  |         :
       | HTTPS        |     :                   |       |                      |         :
       |              +---------(WSS)-----------o Agent o---------(WSS)--------+         :
    Invigilator             :                   |       |                                :
      Browser               :                   +-------+                                :
```

KTP Controller consists of three **main** components:
- Agent (`ktp_controller/agent/`)
- API (`ktp_controller/api/`)
- Web UI (`ktp_controller/wui/`)

Agent is at the heart of this project. It communicates with
Exam-O-Matic and Abitti2 and is responsible for making them play well
together. It uses API to store necessary data in a persistent database
storage. Web UI provides invigilators tools to monitor and control the
exam and admins tools to manage KTP Controller itself. Web UI access
is proxied by Exam-O-Matic via VPN.

The API application is built on FastAPI (https://fastapi.tiangolo.com/).

Dependencies of this project are managed with UV (https://github.com/astral-sh/uv).

The database access is abstracted with SQLAlchemy (https://www.sqlalchemy.org/).

Database migrations are handled by Alembic (https://alembic.sqlalchemy.org/en/latest/).

Processes are launched and kept running with Supervisor (https://supervisord.org/).


## Development instructions

Install development tools with `make dev-install`. It installs `uv` to
`~/.local/bin`. All other packages are installed BY `uv` to a separate
virtual env.

Code must always be formatted with `make format`.

Code must always pass `make check` and `make test`.

Always keep `CHANGELOG.md` up to date.


### How to update dependencies

To update the lock file with new releases of all dependencies, and to
record the set of packages to `uv.lock`, run `make update-deps`. If
the set of packages is ok, remember to commit the lock file with:

```
git commit uv.lock -m 'Update dependencies'
```

### How to run

Simply just run:
```
./dev-run
```
