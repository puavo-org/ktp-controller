#!/bin/bash

set -eu

thisscript=$(readlink -e "$0")
thisdir=$(dirname "${thisscript}")

packages=()
terminate_session=false

if [ -e /dev/virtio-ports/com.redhat.spice.0 ]; then
  if ! [ -e /usr/sbin/spice-vdagentd ]; then
    packages+=("spice-vdagent")
    terminate_session=true
  fi
fi

if [ "${#packages[@]}" -gt 0 ]; then
  sudo apt update
  sudo apt install -y "${packages[@]}"
fi

if [ -e /dev/virtio-ports/com.redhat.spice.0 ]; then
    sudo systemctl start spice-vdagentd
fi

authkeysfile=$(readlink -e ~/.ssh/authorized_keys)

id git 2>&2 || {
    sudo useradd --shell /usr/bin/git-shell --create-home git
    sudo -u git mkdir -p /home/git/.ssh
}

sudo sh -c 'cat >/etc/ssh/sshd_config.d/git.conf <<EOF
Match User git
    AllowGroups git
    X11Forwarding no
    AllowTcpForwarding no
    MaxSessions 1
    PermitTTY no
EOF'
sudo systemctl restart ssh

sudo sh -c "cat '$authkeysfile' /home/puavo-ers/.ssh/id_ecdsa.pub >/home/git/.ssh/authorized_keys"
sudo chown git:git /home/git/.ssh/authorized_keys
sudo -u git sh -c 'cd /home/git; [ -d ktp-controller.git ] || git init --bare ktp-controller.git'

for g in puavo; do
    groups puavo-ers | tr ' ' '\n' | grep -x "$g" || {
        sudo adduser puavo-ers "$g"
        terminate_session=true
    }
done

if ${terminate_session}; then
    sudo loginctl terminate-user puavo-ers
fi
