.PHONY: all
all: ktp_controller/api/ktp_controller.sqlite

ktp_controller/api/ktp_controller.sqlite:
	poetry run alembic upgrade head

.PHONY: format
format:
	poetry run black .

.PHONY: check-format
check-format:
	poetry run black --check .

.PHONY: check
check: check-format
	poetry run flake8 ./ktp_controller/ ./bin/* ./integration_tests/examomatic-mock ./supervisor/chainer
	poetry run pylint --verbose ./ktp_controller/ ./bin/* ./integration_tests/examomatic-mock ./supervisor/chainer

.PHONY: pytest
pytest:
	KTP_CONTROLLER_DOTENV=tests/test.env poetry run pytest --show-capture=all --ff -x --log-level=WARNING --log-cli-level=WARNING --doctest-modules -vv tests/ ktp_controller/

.PHONY: dev-run
dev-run: ktp_controller/api/ktp_controller.sqlite
	poetry run supervisord -c supervisor/dev-run.conf

.PHONY: test
test: ktp_controller/api/ktp_controller.sqlite
	poetry run supervisord -c supervisor/test.conf
	@grep -q -x ok supervisor/chain_result

.PHONY: dev-install
dev-install:
	pip install --user --upgrade --break-system-packages poetry
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

.PHONY: check-updates
check-updates:
	@poetry update --dry-run
	@wget -q -O- https://github.com/redis/redis/releases/latest | sed -r -n 's|.*<title>Release ([0-9.]+).*$$|Redis available: \1|p'
	@sed -r -n 's|^command=docker pull redis:(.*)$$|Redis installed: \1|p' supervisor/test.conf
