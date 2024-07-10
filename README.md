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

```bash
ubuntu@infra1:~$ maas-anvil cluster bootstrap \
    --role database --role region --role agent --role haproxy \
    --accept-defaults
```

Note: You will be asked for a `virtual_ip` during installation of the HAProxy charm, if `accept-defaults` is omitted.
Pass an empty value to disable it, or any valid IP to enable; the Keepalived charm will be installed to enable connecting to HA MAAS using the VIP.

#### PostgreSQL max_connections

You will be asked for a `max_connections` during installation of the PostgreSQL charm, if `accept-defaults` is omitted. Use `default` if you need the default values of PostgreSQL to be applied to [max_connections](https://www.postgresql.org/docs/14/runtime-config-connection.html). If you are aiming for MAAS HA though you have to do one of the following:

- If number of MAAS region nodes is known beforehand, you can calculate the desired max_connections and set them, based on the formula: `max_connections = max(100, 10 + 50 * number_of_region_nodes)`.
- If number of MAAS region nodes is not known, you can set `max_connections` to `dynamic` and let MAAS Anvil recalculate the appropriate PostgreSQL `max_connections` every time a region node is joining or leaving the Anvil cluster. **This options includes a database restart with every modification.**

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

## Cluster updates

You can refresh the cluster by running the `refresh` command:

```bash
ubuntu@infra1:~$ maas-anvil refresh
```

## Cluster updates

You can refresh the cluster by running the `refresh` command:

```bash
ubuntu@infra1:~$ maas-anvil refresh
```

# Managing the cluster after initial deployment

## Juju permission denied

If you get an error message such as:
```bash
please enter password for $node on anvil-controller:
```

It is because Juju oauth macaroons typically expire after 24h.
If you need to interact with the MAAS-anvil Juju controller after this time has passed, you will need to re-authenticate your session.

You can do this directly using the MAAS-anvil command:

```bash
ubuntu@$node:~$ maas-anvil juju-login
```

You can also manually fetch the login credentials from anvil with:

```bash
ubuntu@$node:~$ cat ~/snap/maas-anvil/current/account.yaml
password: $password
user: $user
```

And `juju login` as usual.

### Charm documentation

- MAAS Region: <https://charmhub.io/maas-region>
- MAAS Region: <https://charmhub.io/maas-agent>
- PostgreSQL: <https://charmhub.io/postgresql>
- PgBouncer: <https://charmhub.io/pgbouncer>
- HAProxy: <https://charmhub.io/haproxy>
- Keepalived: <https://charmhub.io/keepalived>
