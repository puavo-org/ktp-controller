.PHONY: all
all: ktp_controller/api/ktp_controller.sqlite

ktp_controller/api/ktp_controller.sqlite:
	poetry run alembic upgrade head

.PHONY: check
check:
	poetry run pylint --verbose ktp_controller

.PHONY: test
test:
	poetry run pytest --doctest-modules -vv tests ktp_controller

.PHONY: dev-run
dev-run: ktp_controller/api/ktp_controller.sqlite
	poetry run uvicorn ktp_controller.api.main:APP --reload

.PHONY: dev-install
dev-install:
	poetry install

.PHONY: dev-update
dev-update:
	poetry update

.PHONY: dev-clean
dev-clean:
	rm -f ktp_controller/api/ktp_controller.sqlite

.PHONY: dev-migratedb
dev-migratedb:
	poetry run alembic upgrade head
