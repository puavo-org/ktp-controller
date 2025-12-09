#!/bin/sh

set -eu

thisscript=$(readlink -e "$0")
thisdir=$(dirname "${thisscript}")

packages=
terminate_session=false

command -v poetry || {
  packages="${packages} python3-poetry"
}

if [ -e /dev/virtio-ports/com.redhat.spice.0 ]; then
  if ! [ -e /usr/sbin/spice-vdagentd ]; then
    packages="${packages} spice-vdagent"
    terminate_session=true
  fi
fi

if [ -n "${packages}" ]; then
  sudo apt update
  sudo apt install -y ${packages}
fi

if [ -e /dev/virtio-ports/com.redhat.spice.0 ]; then
    sudo systemctl start spice-vdagentd
fi

sudo rsync -r --delete-after "$(git rev-parse --show-toplevel)/" /home/puavo-ers/ktp-controller/
sudo chown -R puavo-ers:puavo-ers /home/puavo-ers/ktp-controller

for g in puavo; do
    groups puavo-ers | tr ' ' '\n' | grep -x "$g" || {
        sudo adduser puavo-ers "$g"
        terminate_session=true
    }
done

if ${terminate_session}; then
    sudo loginctl terminate-user puavo-ers
fi
