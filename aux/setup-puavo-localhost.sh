#!/bin/sh

set -eu

thisscript=$(readlink -e "$0")
thisdir=$(dirname "${thisscript}")

command -v poetry || {
  sudo apt update
  sudo apt install -y python3-poetry
}
sudo rsync -r --delete-after "$(git rev-parse --show-toplevel)/" /home/puavo-ers/ktp-controller/
sudo chown -R puavo-ers:puavo-ers /home/puavo-ers/ktp-controller
#sudo install -m0640 -oroot -groot /dev/null /etc/sudoers.d/ktp-controller
#sudo sh -c "echo '%puavo-ers      ALL = (:puavo) NOPASSWD: /usr/bin/make dev-run' >>/etc/sudoers.d/ktp-controller"
head -n1 /etc/resolv.conf | grep -n -x 'nameserver 9.9.9.9' /etc/resolv.conf || {
  sudo sed -r -i '1 i nameserver 9.9.9.9' /etc/resolv.conf
}

groups_changed=false
for g in puavo; do
    groups puavo-ers | tr ' ' '\n' | grep -x "$g" || {
        groups_changed=true
        sudo adduser puavo-ers "$g"
    }
done

if ${groups_changed}; then
    sudo loginctl terminate-user puavo-ers
fi
