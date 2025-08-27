# ktp-controller

## Development

The application is built on FastAPI (https://fastapi.tiangolo.com/).

Dependencies of this project are managed with Poetry (https://python-poetry.org/).

The database access is abstracted with SQLAlchemy (https://www.sqlalchemy.org/).

Database migrations are handled by Alembic (https://alembic.sqlalchemy.org/en/latest/).


### Create new development environment

To create a new virtual environment and install all the required packages, run:
```
poetry install
```

Create/upgrade the local SQLite database file:
```
poetry run alembic upgrade head
```


### Run locally

Run the app:
```
poetry run uvicorn main:app --reload
```

Interactive API documentation: http://127.0.0.1:8000/docs


### Update dependencies

To update the virtual environment with new releases of all dependencies, and to record the set of packages to `poetry.lock`, run:
```
poetry update
```

If the set of packages is ok, remember to commit the lock file:
```
git commit poetry.lock -m 'poetry update'
```
