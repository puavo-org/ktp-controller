#!/bin/bash

set -euo pipefail

on_exit()
{
    set +e

    if [ $exitval -ne 0 ]; then
        echo "🔥 Building for Python ${pyversion} failed!" >&2
        exit 1
    fi

    exit 0
}

exitval=1
pyversion=$1
shift
dir=$1
shift

prefix="${dir}/"

trap on_exit EXIT

export UV_PYTHON="${pyversion}"
export UV_MANAGED_PYTHON=1

echo "📦 Building wheel for Python ${pyversion}..." >&2
uv build --wheel

echo "📄 Exporting dependencies for Python ${pyversion}..." >&2
uv export --no-emit-project --no-dev --format requirements-txt >dist/requirements.txt

echo "🚚 Collecting packages..." >&2
uv pip install \
    -r dist/requirements.txt \
    dist/*.whl \
    --prefix "$prefix"

exitval=0
