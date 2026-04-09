integration_test_case_targets := integration-test-case1 integration-test-case2 integration-test-case3 integration-test-case5 integration-test-case7

.NOTPARALLEL: all
.PHONY: all
all: check test build

.PHONY: format
format:
	uv run ruff format

.PHONY: check-format
check-format:
	uv run ruff format --check

.PHONY: check-alembic
check-alembic:
	rm -f ktp_controller_alembic_check.sqlite
	KTP_CONTROLLER_DB_PATH=ktp_controller_alembic_check.sqlite uv run alembic upgrade head
	KTP_CONTROLLER_DB_PATH=ktp_controller_alembic_check.sqlite uv run alembic check

.PHONY: check
check: check-format check-alembic
	uv run ruff check

.PHONY: pytest
pytest:
	uv run pytest -rA --ignore-glob=tests/integration_test_case*.py --show-capture=all --ff -x --log-level=WARNING --doctest-modules -vv tests/ ktp_controller/

.PHONY: .pytest-integration
.pytest-integration:
	test -n "$${KTP_CONTROLLER_INTEGRATION_TEST_CASE:-}"
	uv run pytest -rA --show-capture=all -x --log-level=WARNING -vv "tests/integration_test_$${KTP_CONTROLLER_INTEGRATION_TEST_CASE}.py"

.PHONY: test
test:
	uv run supervisord -c supervisor/test.conf
	@grep -q -x ok chain_result

.PHONY: $(integration_test_case_targets)
$(integration_test_case_targets): integration-test-%:
	KTP_CONTROLLER_DOTENV='$(@:%=%.env)' KTP_CONTROLLER_INTEGRATION_TEST_CASE='$(@:integration-test-%=%)' uv run supervisord -c supervisor/integration-test.conf
	@grep -q -x ok chain_result

.NOTPARALLEL: integration-test
.PHONY: integration-test
integration-test: $(integration_test_case_targets)

.PHONY: dev-install
dev-install:
	command -v uv >/dev/null || { curl -LsSf https://astral.sh/uv/install.sh | sh; }

.PHONY: update-deps
update-deps:
	uv lock --upgrade

.PHONY: dry-update-deps
dry-update-deps:
	@uv lock --upgrade --dry-run
	@wget -q -O- https://github.com/redis/redis/releases/latest | sed -r -n 's|.*<title>Release ([0-9.]+).*$$|Redis available: \1|p'
	@sed -r -n 's|^command=docker pull redis:(.*)$$|Redis installed: \1|p' supervisor/test.conf

.PHONY: build-prodbundle
build-prodbundle:
	aux/build-prodbundle.sh

.PHONY: build-wheel
build-wheel:
	uv build --wheel

.PHONY: build-sdist
build-sdist:
	uv build --sdist

.PHONY: build
.NOTPARALLEL: build
build: build-prodbundle build-wheel build-sdist

.PHONY: clean
clean:
	git clean -fdx dist/
	git clean -fdx '*.sqlite'
