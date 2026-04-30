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

echo "📦 Building wheel..." >&2
uv build --wheel

echo "📄 Exporting dependencies..." >&2
uv export --no-emit-project --no-dev --format requirements-txt >dist/requirements.txt

echo "🚚 Collecting packages into bundle..." >&2
version=$(uv version --short)
dir="dist/ktp_controller-prodbundle-${version}"
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
zip --symlinks --quiet -r "../ktp_controller-prodbundle-${version}.zip" ktp-controller

echo "✅ Successfully created 'dist/ktp_controller-prodbundle-${version}.zip'" >&2

exitval=0
