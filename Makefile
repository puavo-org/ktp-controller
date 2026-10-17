integration_test_targets := integration-test-case2 integration-test-case3 integration-test-case5 integration-test-case7 integration-test-case8
project_root := $(shell git rev-parse --show-toplevel)
partial_coverage_files := $(shell find '$(project_root)' -type f -name '.coverage*')

.NOTPARALLEL: all
.PHONY: all
all: check test integration-test docs build

.PHONY: format
format:
	uv run ruff format

.PHONY: check-format
check-format:
	uv run ruff format --check

.PHONY: check-alembic
check-alembic:
	git clean -fdx -- '$(project_root)/workdirs/alembic-check/'
	uv run --directory '$(project_root)/workdirs/alembic-check/' alembic -c ../../alembic.ini upgrade head
	uv run --directory '$(project_root)/workdirs/alembic-check/' alembic -c ../../alembic.ini check

.PHONY: check-types
check-types:
	uv run mypy

.PHONY: i18n-extract
i18n-extract:
	uv run pybabel extract -F '$(project_root)/ktp_controller/wui/babel.cfg' \
		-o '$(project_root)/ktp_controller/wui/locale/messages.pot' '$(project_root)/ktp_controller/wui'

.PHONY: i18n-update
i18n-update: i18n-extract
	uv run pybabel update -i '$(project_root)/ktp_controller/wui/locale/messages.pot' \
		-d '$(project_root)/ktp_controller/wui/locale' -D messages --no-fuzzy-matching

.PHONY: i18n-compile
i18n-compile:
	uv run pybabel compile -d '$(project_root)/ktp_controller/wui/locale' -D messages --statistics

.PHONY: check-i18n
check-i18n: i18n-compile
	git diff --exit-code '$(project_root)/ktp_controller/wui/locale'

.NOTPARALLEL: check
.PHONY: check
check: check-format check-alembic check-types check-i18n
	uv run ruff check

.combined_coverage: $(partial_coverage_files)
	uv run coverage combine --data-file='$@' --keep $^

.PHONY: check-coverage
check-coverage: .combined_coverage
	uv run coverage report --data-file='$<' --include 'ktp_controller/*' --omit 'ktp_controller/examomatic/mock/*' --skip-empty --skip-covered

htmlcov: .combined_coverage
	uv run coverage html --data-file='$<' --include 'ktp_controller/*' --omit 'ktp_controller/examomatic/mock/*' --skip-covered --show-contexts --title 'KTP Controller test coverage'

coverage.json: .combined_coverage
	uv run coverage json --data-file='$<' --include 'ktp_controller/*' --omit 'ktp_controller/examomatic/mock/*' --show-contexts --pretty-print

.PHONY: unit-test
unit-test: test

.PHONY: test
test:
	git clean -fdx -- '$(project_root)/workdirs/unit-test/'
	'$(project_root)/aux/unit-test-run'
	@grep -q -x ok '$(project_root)/workdirs/unit-test/chain_result'

.PHONY: $(integration_test_targets)
$(integration_test_targets): integration-test-%:
	git clean -fdx -- '$(project_root)/workdirs/integration-test/$(@:integration-test-%=%)/'
	'$(project_root)/aux/integration-test-run' '$(@:integration-test-%=%)'
	@grep -q -x ok '$(project_root)/workdirs/integration-test/$(@:integration-test-%=%)/chain_result'

.NOTPARALLEL: integration-test
.PHONY: integration-test
integration-test: $(integration_test_targets)

.PHONY: dev-run
dev-run:
	'$(project_root)/dev-run'

.PHONY: dev-install
dev-install:
	command -v uv >/dev/null || { curl -LsSf https://astral.sh/uv/install.sh | sh; }

.PHONY: update-deps
update-deps:
	uv lock --upgrade

.PHONY: dry-update-deps
dry-update-deps:
	@uv lock --upgrade --dry-run

.PHONY: build-prodbundle
build-prodbundle:
	git clean -fdx -- '$(project_root)/'
	'$(project_root)/aux/build-prodbundle.sh'

.PHONY: build-wheel
build-wheel:
	uv build --directory '$(project_root)' --wheel

.PHONY: build-sdist
build-sdist:
	uv build --directory '$(project_root)' --sdist

.NOTPARALLEL: build
.PHONY: build
build: build-prodbundle build-wheel build-sdist

.PHONY: docs
docs:
	uv run python '$(project_root)/aux/generate_status_report_docs.py' '$(project_root)/docs/status_report.md'

.PHONY: clean
clean:
	rm -rf '$(project_root)/htmlcov' '$(project_root)/.mypy_cache' '$(project_root)/.ruff_cache' '$(project_root)/.pytest_cache' '$(project_root)/.venv' '$(project_root)/dist'
	rm -f '$(project_root)/coverage.json' '$(project_root)/.combined_coverage'
	py3clean '$(project_root)/'

.PHONY: gitclean
gitclean:
	git clean -fdx -- '$(project_root)/'
