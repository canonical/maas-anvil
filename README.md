# MAAS Anvil

A snap for managing charmed MAAS deployments.

## MAAS Anvil is currently in a closed beta stage, approaching production stability

## Multi-node installation steps

The following instructions assume that nodes `infra1`, `infra2`, `infra3` are deployed with Ubuntu 22.04 LTS and their networking is properly configured.

In addition, the instructions assume that MAAS Anvil will deploy all the available components (roles) in all three nodes:

- MAAS region controller
- MAAS rack controller (agent)
- PostgreSQL
- HAProxy

### Preparation steps for each node

```bash
ubuntu@infra{1,2,3}:~$ sudo snap install maas-anvil --edge
ubuntu@infra{1,2,3}:~$ maas-anvil prepare-node-script | bash -x
ubuntu@infra{1,2,3}:~$ newgrp snap_daemon
```

### Bootstrap the first node

Note: If accept defaults is not passed, you will be asked for a `virtual_ip` during installation of the HAProxy charm.
Pass an empty value to disable it, or any valid IP to enable; the Keepalived charm will be installed to enable connecting to HA MAAS using the VIP.

```bash
ubuntu@infra1:~$ maas-anvil cluster bootstrap \
    --role database --role region --role agent --role haproxy \
    --accept-defaults
```

### Add new nodes to the MAAS cluster

```bash
ubuntu@infra1:~$ maas-anvil cluster add --name infra2.
Token for the Node infra2.: eyJuYW1lIjoibWFhcy00Lm1hYXMiLCJzZWNyZXQiOiI3MmE512342abcdEASWWxOWNlYWNkYmJjMWRmMjk4OThkYWFkYzQzMDAzZjk4NmRkZDI2MWRhYWVkZTIxIiwiZmluZ2VycHJpbnQiOiJlODU5ZmY5NjAwMDU4OGFjZmQ5ZDM0NjFhMDk5NmU1YTU3YjhjN2Q2ZjE4M2NjZDRlOTg2NGRkZjQ3NWMwZWM1Iiwiam9pbl9hZGRyZXNzZXMiOlsiMTAuMjAuMC43OjcwMDAiLCIxMC4yMC4wLjg6NzAwMCJdfQ==

ubuntu@infra1:~$ maas-anvil cluster add --name infra3.
Token for the Node infra3.: eyJuYW1lIjoibWFhcy00Lm1hYXMiLCJzZWNyZXQiOiI3MmE512342abcdEASWWxOWNlYWNkYmJjMWRmMjk4OThkYWFkYzQzMDAzZjk4NmRkZDI2MWRhYWVkZTIxIiwiZmluZ2VycHJpbnQiOiJlODU5ZmY5NjAwMDU4OGFjZmQ5ZDM0NjFhMDk5NmU1YTU3YjhjN2Q2ZjE4M2NjZDRlOTg2NGRkZjQ3NWMwZWM1Iiwiam9pbl9hZGRyZXNzZXMiOlsiMTAuMjAuMC43OjcwMDAiLCIxMC4yMC4wLjg6NzAwMCJdfQ==
```

### Join new nodes to the MAAS cluster

```bash
ubuntu@infra2:~$ maas-anvil cluster join \
    --role database --role region --role agent --role haproxy \
    --token eyJuYW1lIjoibWFhcy00Lm1hYXMiLCJzZWNyZXQiOiI3MmE512342abcdEASWWxOWNlYWNkYmJjMWRmMjk4OThkYWFkYzQzMDAzZjk4NmRkZDI2MWRhYWVkZTIxIiwiZmluZ2VycHJpbnQiOiJlODU5ZmY5NjAwMDU4OGFjZmQ5ZDM0NjFhMDk5NmU1YTU3YjhjN2Q2ZjE4M2NjZDRlOTg2NGRkZjQ3NWMwZWM1Iiwiam9pbl9hZGRyZXNzZXMiOlsiMTAuMjAuMC43OjcwMDAiLCIxMC4yMC4wLjg6NzAwMCJdfQ==
```

```bash
ubuntu@infra3:~$ maas-anvil cluster join \
    --role database --role region --role agent --role haproxy \
    --token eyJuYW1lIjoibWFhcy00Lm1hYXMiLCJzZWNyZXQiOiI3MmE512342abcdEASWWxOWNlYWNkYmJjMWRmMjk4OThkYWFkYzQzMDAzZjk4NmRkZDI2MWRhYWVkZTIxIiwiZmluZ2VycHJpbnQiOiJlODU5ZmY5NjAwMDU4OGFjZmQ5ZDM0NjFhMDk5NmU1YTU3YjhjN2Q2ZjE4M2NjZDRlOTg2NGRkZjQ3NWMwZWM1Iiwiam9pbl9hZGRyZXNzZXMiOlsiMTAuMjAuMC43OjcwMDAiLCIxMC4yMC4wLjg6NzAwMCJdfQ==
```

### Confirm the cluster status

```bash
ubuntu@infra1:~$ maas-anvil cluster list
┏━━━━━━━━┳━━━━━━━━┳━━━━━━━━┳━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┓
┃ Node   ┃ Status ┃ Region ┃ Agent ┃ Database ┃ HAProxy ┃
┡━━━━━━━━╇━━━━━━━━╇━━━━━━━━╇━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━┩
│ infra1 │   up   │   x    │   x   │    x     │    x    │
│ infra2 │   up   │   x    │   x   │    x     │    x    │
│ infra3 │   up   │   x    │   x   │    x     │    x    │
└────────┴────────┴────────┴───────┴──────────┴─────────┘
```

### Create MAAS admin user

```bash
ubuntu@infra1:~$ juju run maas-region/0 create-admin username=admin password=pass email=admin@maas.io ssh-import=lp:maasadmin
```

### Charm documentation

- MAAS Region: <https://charmhub.io/maas-region>
- MAAS Region: <https://charmhub.io/maas-agent>
- PostgreSQL: <https://charmhub.io/postgresql>
- HAProxy: <https://charmhub.io/haproxy>
- Keepalived: <https://charmhub.io/keepalived>
