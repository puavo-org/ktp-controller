.PHONY: all
all: ktp_controller/api/ktp_controller.sqlite

ktp_controller/api/ktp_controller.sqlite:
	poetry run alembic upgrade head

.PHONY: check
check:
	poetry run pylint --verbose ktp_controller examomatic-listener abitti2-listener

.PHONY: test
test:
	poetry run pytest --doctest-modules -vv tests ktp_controller

.PHONY: dev-run-api
dev-run-api: ktp_controller/api/ktp_controller.sqlite
	poetry run ./api

.PHONY: dev-run-examomatic-listener
dev-run-examomatic-listener:
	poetry run ./examomatic-listener

.PHONY: dev-run-abitti2-listener
dev-run-abitti2-listener:
	poetry run ./abitti2-listener

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
