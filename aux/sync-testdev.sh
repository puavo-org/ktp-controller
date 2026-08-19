#!/bin/sh

set -eu

rsync -rlv --delete-excluded --exclude 'logs/*.log' --exclude 'logs/**/*.log' --exclude .git --exclude .mypy_cache --exclude dist/ --exclude .pytest_cache --exclude .ruff_cache --exclude .venv --exclude __pycache__  --delete-after ./ ktp_controller_testdev:ktp-controller/
