#!/bin/bash

# This script creates zipped relocatable bundle.

set -euo pipefail

on_exit()
{
    set +e

    if [ $exitval -ne 0 ]; then
        echo "🔥 Bundling failed!" >&2
        exit 1
    fi

    exit 0
}

exitval=1

trap on_exit EXIT

export UV_PYTHON=3.11.1
export UV_MANAGED_PYTHON=1

echo "📦 Building wheel..." >&2
uv build --wheel

echo "📄 Exporting dependencies..." >&2
uv export --no-emit-project --no-dev --format requirements-txt >dist/requirements.txt

echo "🚚 Collecting packages into bundle..." >&2
version=$(uv version --short)
pyversion=$(echo -n "${UV_PYTHON}" | tr '.' '_')
bundle_name="ktp_controller-prodbundle-py${pyversion}-${version}"
dir="dist/${bundle_name}"
rm -rf "$dir"
mkdir -p "$dir"
uv pip install \
    -r dist/requirements.txt \
    dist/*.whl \
    --prefix "$dir/ktp-controller/"

echo "🚀 Installing launchers..." >&2
cp -v supervisor/*-prod-run.conf "$dir/ktp-controller/"
cp -v alembic.ini "$dir/ktp-controller/"
cp -v -r alembic "$dir/ktp-controller/"
cp -v aux/launcher "$dir/ktp-controller/ktp-controller"
cp -v LICENSE "$dir/ktp-controller/"
cp -v CHANGELOG.md "$dir/ktp-controller/"
cp -v aux/pyvenv.cfg "$dir/ktp-controller/"
ln -vsf /usr/bin/python3 "$dir/ktp-controller/bin/python3"
ln -vsf python3 "$dir/ktp-controller/bin/python"

find "$dir/ktp-controller/bin" -type f -exec sed -i '1 s|^#!.*\(python[0-9]*\).*|#!/opt/ktp-controller/bin/\1|' {} \;

echo "🗜️ Packing the bundle..." >&2
cd "$dir"
zip --symlinks --quiet -r "../${bundle_name}.zip" ktp-controller

echo "✅ Successfully created 'dist/${bundle_name}.zip'" >&2

exitval=0
