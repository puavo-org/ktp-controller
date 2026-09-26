#!/bin/sh

set -eu


if [ $# -eq 0 ]; then
    remote_host='ktp_controller_testdev'
else
    remote_host="$1"
    shift
fi

thisdir=$(dirname "$0")

rsync "${thisdir}/setup-puavo-os-localhost-for-development.sh" "${remote_host}:"
ssh "${remote_host}" ./setup-puavo-os-localhost-for-development.sh
