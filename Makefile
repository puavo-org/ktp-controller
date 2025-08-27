.PHONY: all
all: ktp_controller/ktp_controller.sqlite

ktp_controller/ktp_controller.sqlite:
	poetry run alembic upgrade head

.PHONY: check
check:
	poetry run pylint --verbose ktp_controller

.PHONY: test
test:
	poetry run pytest -vv

.PHONY: dev-run
dev-run: ktp_controller/ktp_controller.sqlite
	poetry run uvicorn ktp_controller.main:APP --reload

.PHONY: dev-install
dev-install:
	poetry install

.PHONY: dev-update
dev-update:
	poetry update

.PHONY: dev-clean
dev-clean:
	rm -f ktp_controller/ktp_controller.sqlite

.PHONY: dev-migratedb
dev-migratedb:
	poetry run alembic upgrade head
