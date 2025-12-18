prefix = /usr
exec_prefix = $(prefix)
bindir = $(exec_prefix)/bin
datarootdir = $(prefix)/share
sysconfdir = /etc

INSTALL = install
INSTALL_PROGRAM = $(INSTALL)
INSTALL_DATA = $(INSTALL) -m 644

_build_formats := sdist wheel
_build_targets := $(_build_formats:%=build-%)

.NOTPARALLEL: all
.PHONY: all
all: check test build

.PHONY: installdirs
installdirs:
	mkdir -p $(DESTDIR)/opt/ktp-controller
	mkdir -p $(DESTDIR)/opt/ktp-controller/alembic
	mkdir -p $(DESTDIR)/opt/ktp-controller/alembic/versions
	mkdir -p $(DESTDIR)/opt/ktp-controller/ktp_controller
	mkdir -p $(DESTDIR)/opt/ktp-controller/ktp_controller/abitti2
	mkdir -p $(DESTDIR)/opt/ktp-controller/ktp_controller/api
	mkdir -p $(DESTDIR)/opt/ktp-controller/ktp_controller/api/exam
	mkdir -p $(DESTDIR)/opt/ktp-controller/ktp_controller/api/system
	mkdir -p $(DESTDIR)/opt/ktp-controller/ktp_controller/examomatic
	mkdir -p $(DESTDIR)/opt/ktp-controller/supervisor

.PHONY: install
install: installdirs
	$(INSTALL_PROGRAM) -t $(DESTDIR)/opt/ktp-controller \
		bin/agent bin/api bin/cli
	$(INSTALL_DATA) -t $(DESTDIR)/opt/ktp-controller \
		alembic.ini
	$(INSTALL_DATA) -t $(DESTDIR)/opt/ktp-controller/alembic \
		alembic/*.py \
		alembic/script.py.mako
	$(INSTALL_DATA) -t $(DESTDIR)/opt/ktp-controller/alembic/versions \
		alembic/versions/*.py
	$(INSTALL_DATA) -t $(DESTDIR)/opt/ktp-controller/ktp_controller \
		ktp_controller/*.py
	$(INSTALL_DATA) -t $(DESTDIR)/opt/ktp-controller/ktp_controller/abitti2 \
		ktp_controller/abitti2/*.py \
		ktp_controller/abitti2/words.txt
	$(INSTALL_DATA) -t $(DESTDIR)/opt/ktp-controller/ktp_controller/api \
		ktp_controller/api/*.py
	$(INSTALL_DATA) -t $(DESTDIR)/opt/ktp-controller/ktp_controller/api/exam \
		ktp_controller/api/exam/*.py
	$(INSTALL_DATA) -t $(DESTDIR)/opt/ktp-controller/ktp_controller/api/system \
		ktp_controller/api/system/*.py
	$(INSTALL_DATA) -t $(DESTDIR)/opt/ktp-controller/ktp_controller/examomatic \
		ktp_controller/examomatic/*.py \
		ktp_controller/examomatic/dummy-exam-file.mex
	$(INSTALL_DATA) -t $(DESTDIR)/opt/ktp-controller/supervisor \
		supervisor/run.conf

ktp_controller_dev.sqlite:
	poetry run alembic upgrade head

.PHONY: format
format:
	poetry run black .

.PHONY: check-format
check-format:
	poetry run black --check .

.PHONY: check-alembic
check-alembic: ktp_controller_dev.sqlite
	poetry run alembic check

.PHONY: check
check: check-format check-alembic
	poetry run flake8 ./ktp_controller/ ./bin/* ./supervisor/chainer tests/utils.py
	poetry run pylint --verbose ./ktp_controller/ ./bin/* ./supervisor/chainer tests/utils.py

.PHONY: pytest
pytest:
	KTP_CONTROLLER_DOTENV=tests/test.env poetry run pytest -rA --ignore-glob=tests/integration_test_case*.py --show-capture=all --ff -x --log-level=WARNING --doctest-modules -vv tests/ ktp_controller/

.PHONY: pytest-integration
pytest-integration:
	KTP_CONTROLLER_DOTENV=tests/integration_test.env poetry run pytest -rA --show-capture=all -x --log-level=WARNING -vv tests/integration_test_case2.py

.PHONY: dev-run
dev-run: ktp_controller_dev.sqlite
	poetry run supervisord -c supervisor/dev-run.conf

.PHONY: test
test:
	poetry run supervisord -c supervisor/test.conf
	@grep -q -x ok supervisor/chain_result

.PHONY: integration-test
integration-test:
	poetry run supervisord -c supervisor/integration-test.conf
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
	git clean -fdx '*.sqlite'

.PHONY: check-updates
check-updates:
	@poetry update --dry-run
	@wget -q -O- https://github.com/redis/redis/releases/latest | sed -r -n 's|.*<title>Release ([0-9.]+).*$$|Redis available: \1|p'
	@sed -r -n 's|^command=docker pull redis:(.*)$$|Redis installed: \1|p' supervisor/test.conf

.PHONY: $(_build_targets)
$(_build_targets): build-%:
	poetry build --format='$(@:build-%=%)'

.PHONY: build
build: $(_build_targets)

.PHONY: clean
clean:
	rm -rf dist
