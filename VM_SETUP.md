# MAAS Anvil Development VM Setup

For the purpose of developing and testing MAAS Anvil, you will need (up to) three VM's. While one is enough to deploy a non-HA setup, features should be tested in HA. Here, we use LXD VMs.

## LXD Network Setup

First, create an LXD network as shown below. Each VM you create will be assigned an IP address in this network.

```bash
CONTROL_NETWORK_PREFIX="10.30.0"

lxc network create maas-anvil-ctrl
cat << __EOF | lxc network edit maas-anvil-ctrl
config:
  dns.domain: maas-anvil-ctrl
  ipv4.address: ${CONTROL_NETWORK_PREFIX}.1/24
  ipv4.dhcp: "true"
  ipv4.dhcp.ranges: ${CONTROL_NETWORK_PREFIX}.16-${CONTROL_NETWORK_PREFIX}.31
  ipv4.nat: "true"
  ipv6.address: none
description: ""
name: maas-anvil-ctrl
type: bridge
used_by: []
managed: true
status: Created
locations:
- none
__EOF
```

Next, we need to create a second network in order for our VMs to be able to communicate back with the host machine.

```bash
MANAGEMENT_NETWORK_PREFIX="10.40.0"

lxc network create maas-anvil-kvm
cat << __EOF | lxc network edit maas-anvil-kvm
config:
  ipv4.address: ${MANAGEMENT_NETWORK_PREFIX}.1/24
  ipv4.dhcp: "false"
  ipv4.nat: "true"
  ipv6.address: none
description: ""
name: maas-kvm
type: bridge
used_by: []
managed: true
status: Created
locations:
- none
__EOF

lxc config set core.https_address [::]:8443
```

## LXD Profile Setup

Next, we need to create an LXD profile for our VMs. This will set memory and cpu requirements, configure the default installed packages, copy your ssh key into the VMs so you can access them, and mount your clone of `maas-anvil` into the VM.

```bash
# This needs to point to where you have maas-anvil cloned
MAAS_ANVIL_SRC="/home/your_username/maas-repos/maas-anvil"
PROFILE_NAME="anvil"

lxc profile create ${PROFILE_NAME}
cat <<EOF | lxc profile edit ${PROFILE_NAME}
config:
    limits.memory: 4GB
    limits.cpu: "4"
    raw.idmap: |
        uid $(id -u) 1000
        gid $(id -g) 1000
    user.vendor-data: |
        #cloud-config
        packages:
        - git
        - build-essential
        - jq
        - snapcraft
        runcmd:
        - cat /dev/zero | ssh-keygen -q -N ""
        ssh_authorized_keys:
        - $(cat ${HOME}/.ssh/id_rsa.pub | cut -d' ' -f1-2)
description: MAAS Anvil environment
devices:
    root:
        path: /
        pool: default
        type: disk
        size: 50GB
    work:
        type: disk
        source: ${MAAS_ANVIL_SRC}
        path: /work
    eth0:
        type: nic
        name: eth0
        network: maas-anvil-ctrl
    eth1:
        type: nic
        name: eth1
        network: maas-anvil-kvm
EOF
```

## Launch the VMs

To create your VMs, execute the following:

```bash
lxc launch ubuntu:22.04 infra1 --vm -p ${PROFILE_NAME}
lxc launch ubuntu:22.04 infra2 --vm -p ${PROFILE_NAME}
lxc launch ubuntu:22.04 infra3 --vm -p ${PROFILE_NAME}
```

If you are running these commands in a script, include the lines below to wait for the VMs to be ready.

```bash
# this sleep may not be necessary, or may be shortened depending on your system
sleep 10
lxc exec infra1 -- cloud-init status --wait
lxc exec infra2 -- cloud-init status --wait
lxc exec infra3 -- cloud-init status --wait
```

## Set up VMs Internally and Install MAAS Anvil

We now need to execute some commands in each VM. This will set up our second network interface, setup LXD inside the VM, and build & install the MAAS Anvil snap.

```bash
KVM_NETWORK_PREFIX="10.40.0"

sudo tee /etc/netplan/99-maas-kvm-net.yaml <<EOF
network:
    version: 2
    ethernets:
        enp6s0:
            addresses:
                - ${KVM_NETWORK_PREFIX}.2/24
EOF
sudo netplan apply

lxd init --auto

sleep 5
cd /work
/usr/bin/make snap
sudo snap install ./maas-anvil.snap --dangerous
```

To execute this inside the VM from a script running on your host machine, save the contents above to a file (below, `/path/to/script`), then run:

```bash
infra1_ip=$(lxc exec infra1 -- hostname -I | cut -d " " -f 1)
ssh -o "StrictHostKeyChecking no" ubuntu@${infra1_ip} bash -s < /path/to/script
```

## Set up MAAS Anvil snap

Finally, we need to:

- Delete the default bridge interface created by `lxd init --auto`, as having this interface active may cause the MAAS region charm to assign itself to this network.
- Run the `prepare-node-script` provided by MAAS Anvil
- Login to the `snap_daemon` group
- Create a self-signed SSL certificate, to optionally be used for MAAS Anvil TLS configuration

```bash
sudo ip link delete lxdbr0

maas-anvil prepare-node-script | bash -x

newgrp snap_daemon

openssl req -new -x509 -nodes -subj "/C=US/ST=Colorado/L=Denver/O=MAAS/OU=Anvil/CN=infra1.maas-anvil-ctrl" -keyout /home/ubuntu/.config/anvil/key.pem -out /home/ubuntu/.config/anvil/cert.pem -days 3650
```

You should now have three VMs setup: `infra1`, `infra2`, and `infra3` where you can bootstrap/join the cluster.

## Rebuilding

To make changes to the code and rebuild the snap, you'll need to delete each VM (`lxc delete --force infra{1,2,3}`) and restart this process again. While this is cumbersome, we currently do not have a better way to achieve this until we are able to leave the `lxdbr0` interface active.
