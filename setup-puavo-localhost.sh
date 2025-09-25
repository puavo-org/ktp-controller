#!/bin/sh

set -eu

thisscript=$(readlink -e "$0")
thisdir=$(dirname "${thisscript}")

command -v poetry || {
  sudo apt update
  sudo apt install -y python3-poetry
}
sudo rsync -r --delete-after "${thisdir}/" /home/puavo-ers/ktp-controller/
sudo chown -R puavo-ers:puavo-ers /home/puavo-ers/ktp-controller
sudo install -m0640 -oroot -groot /dev/null /etc/sudoers.d/ktp-controller
sudo sh -c "echo '%puavo-ers      ALL = (:puavo) NOPASSWD: /usr/bin/make dev-run' >>/etc/sudoers.d/ktp-controller"
