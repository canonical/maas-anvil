# MAAS Anvil

MAAS Anvil is a snap for managing a charmed (HA) MAAS deployment.

> [!IMPORTANT]
> MAAS Anvil is currently in a closed beta stage, approaching production stability

##### MAAS Deployment Components

MAAS Anvil is part of the MAAS deployment strategy, which includes:

1. **MAAS Charms**: [Charmed](https://juju.is/docs/juju/charmed-operator) versions of MAAS components.
    - [MAAS Agent Charm](https://charmhub.io/maas-agent)
    - [MAAS Region Charm](https://charmhub.io/maas-region)
2. [**MAAS Anvil**](https://github.com/canonical/maas-anvil): Uses MAAS charms to simplify MAAS deployments.
3. [**MAAS Terraform Provider**](https://registry.terraform.io/providers/maas/maas/latest/docs): Configures active MAAS deployments.

MAAS Anvil streamlines the deployment process using MAAS charms. After deployment, the MAAS Terraform provider can be used for further configuration of the active MAAS environment.

# In this documentation

| Serve our study                                                      | Serve our work                                                       |
| :------------------------------------------------------------------- | :------------------------------------------------------------------- |
| [Tutorials](#tutorial) Hands-on introductions to MAAS Anvil features | [How-to guides](#how-to) Step-by-step guides covering key operations |
|                                                                      | [Reference](#reference) Technical specifications                     |

# Tutorial

## Bootstrap a maas-anvil cluster to learn the basics

The following instructions assume that you have three nodes `infra1`, `infra2`, `infra3` running Ubuntu 22.04 LTS and their networking is configured correctly.

In addition, the instructions assume that MAAS Anvil deploys all available components (roles) on all three nodes:

-   MAAS region controller
-   MAAS rack controller (agent)
-   PostgreSQL
-   HAProxy

### Preparation steps for each node

First, MAAS Anvil needs to be installed and some prerequisites for MAAS Anvil need to be set up. This needs to be done on every node. You can learn more about what `maas-anvil prepare-node-script` does in the CLI interface reference.

```bash
ubuntu@infra{1,2,3}:~$ sudo snap install maas-anvil --edge
ubuntu@infra{1,2,3}:~$ maas-anvil prepare-node-script | bash -x
```

Among other things, the prepare-node-script adds the current user to the `snap_daemon` group. In order for the group changes to take effect, you must `log out` and `log in` again. If the file ownership of groups is not a major concern for you, you can also run the following command to activate the changes to the groups immediately.

```bash
ubuntu@infra{1,2,3}:~$ newgrp snap_daemon
```

### Bootstrap the first node

To initialize the cluster you need to run the bootstrap command on the first node.

```bash
ubuntu@infra1:~$ maas-anvil cluster bootstrap \
    --role database --role region --role agent --role haproxy \
    --accept-defaults
```

> [!NOTE]
> The `--accept-defaults` flag, as the name suggests, accepts the default configuration of MAAS Anvil. The most important configurations are the [virtual IP](#virtual-ip-vip), [PostgreSQL max_connections](#max-connections) and [TLS termination](#tsl). If the `--accept-defaults` flag is omitted, you will be prompted for the configuration during the deployment. If you want to specify the configuration beforehand, you can create a manifest file and provide the manifest file with the `--manifest` flag. [Read more about how to configure your MAAS Anvil deployment with a manifest file](#configure-your-maas-anvil-deployment).

### Add new nodes to the MAAS cluster

To add additional nodes to the cluster, you must first create join tokens on the initial node on which the cluster was bootstrapped. Make sure that you specify the fully qualified domain name (FQDN) of the joining node in the fqdn flag.

```bash
ubuntu@infra1:~$ maas-anvil cluster add --fqdn infra2.
Token for the Node infra2.: eyJuYW1lIjoibWFhcy00Lm1hYXMiLCJzZWNyZXQiOiI3MmE512342abcdEASWWxOWNlYWNkYmJjMWRmMjk4OThkYWFkYzQzMDAzZjk4NmRkZDI2MWRhYWVkZTIxIiwiZmluZ2VycHJpbnQiOiJlODU5ZmY5NjAwMDU4OGFjZmQ5ZDM0NjFhMDk5NmU1YTU3YjhjN2Q2ZjE4M2NjZDRlOTg2NGRkZjQ3NWMwZWM1Iiwiam9pbl9hZGRyZXNzZXMiOlsiMTAuMjAuMC43OjcwMDAiLCIxMC4yMC4wLjg6NzAwMCJdfQ==

ubuntu@infra1:~$ maas-anvil cluster add --fqdn infra3.
Token for the Node infra3.: eyJuYW1lIjoibWFhcy00Lm1hYXMiLCJzZWNyZXQiOiI3MmE512342abcdEASWWxOWNlYWNkYmJjMWRmMjk4OThkYWFkYzQzMDAzZjk4NmRkZDI2MWRhYWVkZTIxIiwiZmluZ2VycHJpbnQiOiJlODU5ZmY5NjAwMDU4OGFjZmQ5ZDM0NjFhMDk5NmU1YTU3YjhjN2Q2ZjE4M2NjZDRlOTg2NGRkZjQ3NWMwZWM1Iiwiam9pbl9hZGRyZXNzZXMiOlsiMTAuMjAuMC43OjcwMDAiLCIxMC4yMC4wLjg6NzAwMCJdfQ==
```

### Join new nodes to the MAAS cluster

Now we have to join the cluster on the joining nodes using the `cluster join` command and the join token that was just created. The roles with which a node joins the cluster can be specific to the node and do not have to match those of the bootstrap node. In this example, we opt for a configuration in which every node has every component.

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

If everything went smoothly, the MAAS-Anvil cluster should now be operational. You can check the status of your cluster with the following command. If you would like to learn more about how to monitor an ongoing MAAS Anvil deployment, you can read more about this in the section [Monitor an ongoing deployment](#monitor-an-ongoing-deployment).

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

To finish up your deployment you can create the MAAS admin user with the following command:

```bash
ubuntu@infra1:~$ juju run maas-region/0 create-admin username=admin password=pass email=admin@maas.io ssh-import=lp:maasadmin
```

You should now have a running MAAS Anvil HA cluster with one admin user ✨.

# How to

## Bootstrap a cluster

This is a shorter version of the [Bootstrap a maas-anvil cluster to learn the basics](#bootstrap-a-maas-anvil-cluster-to-learn-the-basics) tutorial. You can reference this how to, if you have deployed a MAAS Anvil cluster before, but need a refresh on the process.

### Prepare nodes

On each node you need to run the following commands to prepare them for usage with MAAS Anvil:

```bash
ubuntu@infra{1,2,3}:~$ sudo snap install maas-anvil --edge
ubuntu@infra{1,2,3}:~$ maas-anvil prepare-node-script | bash -x
```

Among other things, the prepare-node-script adds the current user to the `snap_daemon` group. In order for the group changes to take effect, you must `log out` and `log in` again. If the file ownership of groups is not a major concern for you, you can also run the following command to activate the changes to the groups immediately.

```bash
ubuntu@infra{1,2,3}:~$ newgrp snap_daemon
```

### Bootstrap the first node

To initialize the cluster you need to run the bootstrap command on the first node.

```bash
ubuntu@infra1:~$ maas-anvil cluster bootstrap \
    --role database --role region --role agent --role haproxy \
    --accept-defaults
```

### Add new nodes

To add a new node to the cluster run the following `cluster add` on the bootstrap node and make note of the tokens.

```bash
ubuntu@infra1:~$ maas-anvil cluster add --fqdn infra2.
Token for the Node infra2.: eyJuYW1lIjoibWFhcy00Lm1hYXMiLCJzZWNyZXQiOiI3MmE512342abcdEASWWxOWNlYWNkYmJjMWRmMjk4OThkYWFkYzQzMDAzZjk4NmRkZDI2MWRhYWVkZTIxIiwiZmluZ2VycHJpbnQiOiJlODU5ZmY5NjAwMDU4OGFjZmQ5ZDM0NjFhMDk5NmU1YTU3YjhjN2Q2ZjE4M2NjZDRlOTg2NGRkZjQ3NWMwZWM1Iiwiam9pbl9hZGRyZXNzZXMiOlsiMTAuMjAuMC43OjcwMDAiLCIxMC4yMC4wLjg6NzAwMCJdfQ==

ubuntu@infra1:~$ maas-anvil cluster add --fqdn infra3.
Token for the Node infra3.: eyJuYW1lIjoibWFhcy00Lm1hYXMiLCJzZWNyZXQiOiI3MmE512342abcdEASWWxOWNlYWNkYmJjMWRmMjk4OThkYWFkYzQzMDAzZjk4NmRkZDI2MWRhYWVkZTIxIiwiZmluZ2VycHJpbnQiOiJlODU5ZmY5NjAwMDU4OGFjZmQ5ZDM0NjFhMDk5NmU1YTU3YjhjN2Q2ZjE4M2NjZDRlOTg2NGRkZjQ3NWMwZWM1Iiwiam9pbl9hZGRyZXNzZXMiOlsiMTAuMjAuMC43OjcwMDAiLCIxMC4yMC4wLjg6NzAwMCJdfQ==
```

### Join new nodes to the cluster

Join the cluster on the joining nodes using the `cluster join` command, the join token that was just created and the roles you want for the specific node.

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

## Log into the Juju controller

If you receive an error message like the following:

```
please enter password for $node on anvil-controller:
```

It is because Juju OAuth macaroons typically expire after 24h. If you need to interact with the MAAS Anvil Juju controller once the macaroon expires, you will need to re-authenticate your session. You can re-authenticate your session with the following command:

```bash
ubuntu@$node:~$ maas-anvil juju-login
```

You can also manually fetch the login credentials from MAAS Anvil with:

```bash
ubuntu@$node:~$ cat ~/snap/maas-anvil/current/account.yaml
password: $password
user: $user
```

And use `juju login` as usual.

## Configure your MAAS Anvil deployment

When deploying MAAS in high availability, you may need to configure the maximum connection to the database, the virtual IP, TSL, the charms versions used or even the way a component is deployed. MAAS Anvil allows you to configure all of these things, and this section explains how to do it.

If you want to know exactly what configuration options are available and what effects they have, please read the section on [Configuration options](#configuration-options).

The configuration options of MAAS Anvil are generally divided into two categories:

-   Deployment
-   Software

In the Deployment category you can configure general options for deployment, in the software category you can select versions and configuration of all charms used in MAAS Anvil and define how these charms are deployed.

### `--accept-defaults` flag

If you set the `--accept-defaults` flag on the bootstrapped and joining nodes you will accept the default configuration that comes with MAAS Anvil. For all available configuration options you can see the default option in the [Configuration options](#configuration-options) section.

### Configuration prompting

If you omit the `--accept-defaults` flag, you will be prompted to enter the deployment configuration during deployment. However, you will not be prompted for the software configuration. The software default settings will still be selected.

### Manifest file

If you want to define the entire configuration of the MAAS Anvil deployment in advance, both deployment and software, you can do so with a manifest file. A manifest file is a yaml file that can be used to specify all configurations for a MAAS Anvil cluster deployment.

Run the following command to generate a manifest file for MAAS Anvil:

```bash
maas-anvil manifest generate
```

A manifest file will be created in the default location `$HOME/.config/anvil/manifest.yaml`. If you have a running MAAS Anvil installation, the manifest file will be based on the configurations of your running MAAS Anvil cluster. If no bootstrap has been performed yet, you will receive a default configuration file that looks something like this:

```yaml
deployment:
  bootstrap:
    # Management networks shared by hosts (CIDRs, separated by comma)
    management_cidr: ""
  postgres:
    # Maximum number of concurrent connections to allow to the database server
    max_connections: "default"
  haproxy:
    # Virtual IP to use for the Cluster in HA
    virtual_ip: ""
    # The TLS mode
    tls_mode: "disabled"
    # Path to SSL Certificate for HAProxy (enter nothing to skip TLS)
    ssl_cert: ""
    # Path to private key for the SSL certificate (enter nothing to skip TLS)
    ssl_key: ""
software:
  # juju:
  #   bootstrap_args: []
  #   scale_args: []
  # charms:
  #   maas-region:
  #     channel: 3.4/edge
  #     revision: null
  #     config: null
  #   maas-agent:
  #     channel: 3.4/edge
  #     revision: null
  #     config: null
  #   haproxy:
  #     channel: latest/stable
  #     revision: null
  #     config: null
  #   postgresql:
  #     channel: 14/stable
  #     revision: null
  #     config: null
  #   keepalived:
  #     channel: latest/stable
  #     revision: null
  #     config: null
  # terraform:
  #   maas-region-plan:
  #     source: /snap/maas-anvil/63/etc/deploy-maas-region
  #   maas-agent-plan:
  #     source: /snap/maas-anvil/63/etc/deploy-maas-agent
  #   haproxy-plan:
  #     source: /snap/maas-anvil/63/etc/deploy-haproxy
  #   postgresql-plan:
  #     source: /snap/maas-anvil/63/etc/deploy-postgresql
```

As mentioned above, you can find a more detailed explanation of all available configuration options in the [Configuration options](#configuration-options) section.

Once you have set up a manifest file to your liking, you can deploy it when you bootstrap your deployment as follows:

```bash
ubuntu@infra1:~$ maas-anvil cluster bootstrap \
    --role database --role region --role agent --role haproxy \
    --manifest "$HOME/.config/anvil/manifest.yaml"
```

If you have already deployed a MAAS Anvil cluster and want to update some configuration after the fact you can also use the `refresh` command to update the cluster with a (new) manifest file.

```bash
ubuntu@infra1:~$ maas-anvil refresh --manifest "$HOME/.config/anvil/manifest.yaml"
```

#### Inspecting manifest files

You can list all previously applied manifest files with the `manifest list` command. It shows you the database ID and the date it was applied to the deployment:

```bash
ubuntu@infra1:~$ maas-anvil manifest list
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
┃ ID                               ┃ Applied Date        ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
│ 0b7bbf2298c2a917dc29fb3d3268366b │ 2024-09-04 10:26:39 │
│ 8fc3764a7ed0036f76cf935eff4a8d75 │ 2024-09-04 10:56:28 │
└──────────────────────────────────┴─────────────────────┘
```

If you want to inspect the contents of one of those manifest files you can show them with the `manifest show` command by providing the ID:

```bash
ubuntu@infra1:~$ maas-anvil manifest show --id 0b7bbf2298c2a917dc29fb3d3268366b
```

## Monitor an ongoing deployment

### With MAAS Anvil

#### `cluster list`

The simplest way to monitor an ongoing MAAS Anvil deployment is with the build in `cluster list` command.

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

#### `inspect`

If you suspect there is something wrong with your MAAS Anvil cluster you might also want to use the `maas-anvil inspect` command. It creates an introspection report of the current state of the cluster.  
You can read more about it in the [CLI reference section](#maas-anvil-inspect).

```bash
ubuntu@infra1:~$ maas-anvil inspect
```

### With Juju

As MAAS Anvil uses Juju to deploy MAAS charms under the hood you can also use the `juju status` command to get more information about the status of an ongoing deployment. For example to monitor the juju status every 5 seconds you can run the following command on any node that is part of the MAAS Anvil cluster

```bash
ubuntu@infra{1,2,3}:~$ juju status --watch 5s
```

## Clean up a MAAS Anvil deployment

> [!IMPORTANT]
> The clean-up process for MAAS Anvil is not yet fully mature. Proceed with caution and at your own risk.

The most reliable way to clean up a MAAS Anvil deployment at the moment is to redeploy the node on which MAAS Anvil was used. However, if you need to clean up the node without redeploying, you can perform the following steps.

### Removing joined nodes

To get started with cleaning up a MAAS Anvil cluster you need to remove the nodes from the cluster. This command needs to be run on the bootstrap node.

```bash
ubuntu@infra1:~$ maas-anvil remove --fqdn infra2.
Removed node infra2. from the cluster
Run command 'sudo /sbin/remove-juju-services' on node infra2. to reuse the machine.
```

This command will remove the node from the cluster and return commands you need to manually run on the removed node.

```bash
ubuntu@infra2:~$ sudo /sbin/remove-juju-services
```

### Cleaning up the bootstrap node

Currently, there is no officially supported method to clean up the bootstrap node. Below are two temporary solutions you can consider until we develop a more comprehensive and officially supported cleanup process:

1. Use the `jhack nuke` command. [This tool](https://github.com/canonical/jhack?tab=readme-ov-file#nuke) can help remove Juju deployments more thoroughly. However, use it with caution and only after understanding its implications.
2. Follow community-sourced cleanup methods. A user has shared their experience and method for cleaning up MAAS Anvil deployments. You can find more information and contribute to the discussion in this GitHub issue: [\#9 Uninstall and cleanup](https://github.com/canonical/maas-anvil/issues/9)

# Reference

## Configuration options

This is a reference for the available configuration options and their effects. If you want to generally understand how to configure your MAAS deployment, read the section [Configure your MAAS Anvil deployment](#configure-your-maas-anvil-deployment).

### Deployment

#### Bootstrap

You can configure Management networks shared by hosts (CIDRs, separated by comma). When deploying without a manifest this is automatically set for you.

###### Manifest example snippet

```yaml
deployment:
  bootstrap:
    # Management networks shared by hosts (CIDRs, separated by comma)
    management_cidr: "10.54.236.0/24"
```

#### Postgres

##### Max connections

> [!NOTE]
> The default value is `max_connection: "default"`

With this option you can configure the maximum number of concurrent connections to allow access to the database server.

###### Default

`default` applies the default values of PostgreSQL to [max_connections](https://www.postgresql.org/docs/14/runtime-config-connection.html). The default is typically 100 connections, but might be less if your kernel settings will not support it (as determined during initdb).

If you are aiming for MAAS HA though you have to do one of the following:

###### Manually setting max_connections

If the number of MAAS region nodes is known beforehand, you can calculate the desired max_connections and set them, based on the formula: `max_connections = max(100, 10 + 50 * number_of_region_nodes)`.

###### Dynamic

If the number of MAAS region nodes is not known, you can set `max_connections` to `dynamic` and let MAAS Anvil recalculate the appropriate PostgreSQL `max_connections` every time a region node is joining or leaving the Anvil cluster.

> [!IMPORTANT]
> With this option set the database will restart with every modification of the MAAS Anvil cluster\!

###### Manifest example snippet

```yaml
deployment:
  postgres:
    # Maximum number of concurrent connections to allow to the database server
    max_connections: "default"
```

#### HA proxy

##### Virtual IP (VIP)

> [!NOTE]
> The default value is `virtual_ip: ""`, so disabled.

You can configure the VIP which should be used for the cluster in High availability (HA). The Keepalived charm will be installed to enable connecting to the MAAS Anvil HA cluster using the VIP. To enable VIP provide any valid IP, to disable it set an empty value.

##### TSL

> [!NOTE]
> The default values are `tls_mode:"disabled"`, `ssl_cert: ""` and `ssl_key: ""`.

To configure TSL for HAProxy, set `tls_mode` either to `termination` or `passthrough` and configure the path to the SSL certificate and the path to the private key for the SSL certificate. To disable it, set `tls_mode` to `disabled` and provide no SSL certificate or private key.  
If `passthrough` is selected, also provide `ssl_cacert` if you want to use a self-signed certificate.

> [!IMPORTANT]
> The certificate and key must be accessible by the `maas-anvil` snap. Make sure these files are in a directory that can be accessed by `maas-anvil`, such as `$HOME/.config/anvil`.

###### Manifest example snippet

```yaml
deployment:
  haproxy:
    # Virtual IP to use for the Cluster in HA
    virtual_ip: ""
    # The TLS mode
    tls_mode: "disabled"
    # Path to SSL Certificate for HAProxy (enter nothing to skip TLS)
    ssl_cert: ""
    # Path to private key for the SSL certificate (enter nothing to skip TLS)
    ssl_key: ""
    # Path to CA certificate, if you want to use a self-signed certificate when
    # in passthrough mode
    ssl_cacert: ""
```

> [!NOTE]
> If haproxy is not to be installed, TLS questions will be asked during the maas-region install step. In this case, `termination` is not a valid `tls_mode`.

### Software

#### Juju

The Juju section allows you to configure extra arguments which will be passed to the `juju bootstrap` (`bootstrap_args`) and `juju enable-ha` (`scale_args`) command. Learn more about [bootstrap arguments](https://juju.is/docs/juju/juju-bootstrap) and [scale arguments](https://juju.is/docs/juju/juju-enable-ha) in the Juju docs.

###### Manifest example snippet

```yaml
juju:
  bootstrap_args: []
  scale_args: []
```

#### Charms

MAAS Anvil is using the following charms:

-   [maas-region](https://charmhub.io/maas-region)
-   [maas-agent](https://charmhub.io/maas-agent)
-   [haproxy](https://charmhub.io/haproxy)
-   [postgresql](https://charmhub.io/postgresql)
-   [keepalived](https://charmhub.io/keepalived)

For each of those charms you manually set the

-   channel
-   revision
-   custom configuration

Check which configuration can be passed to a charm in their respective documentation.

###### Manifest example snippet

```yaml
charms
  maas-region:
    channel: 3.4/edge
    revision: null
    config: null
```

#### Terraform

You can configure the Terraform plans MAAS Anvil uses to, for example, change what the final relations of the cluster look like.

###### Manifest example snippet

```yaml
terraform:
  maas-region-plan:
    source: /snap/maas-anvil/63/etc/deploy-maas-region
  maas-agent-plan:
    source: /snap/maas-anvil/63/etc/deploy-maas-agent
  haproxy-plan:
    source: /snap/maas-anvil/63/etc/deploy-haproxy
  postgresql-plan:
    source: /snap/maas-anvil/63/etc/deploy-postgresql
```

## CLI interface

### `maas-anvil [OPTIONS] COMMAND [ARGS]...`
```
MAAS Anvil is an installer that makes deploying MAAS in HA easy. To get started run the prepare-node-script command and bootstrap the first node. Read more about MAAS Anvil in the documentation.

Commands:  
  Prepare, create and manage a cluster:  
    prepare-node-script  Generates a script to prepare the node for use with MAAS Anvil.  
    cluster bootstrap    Initializes the cluster on the first node.  
    cluster add          Generates a token for a new node to join the cluster.  
    cluster join         Joins the node to a MAAS Anvil cluster when given a valid join  
                         token.

  Configure and update the cluster:  
    manifest generate    Generates a manifest file with which a MAAS Anvil deployment can  
                         be configured.  
    manifest list        Lists the currently active manifest file.  
    manifest show        Shows the manifest data.  
    refresh              Refresh the cluster with a new manifest file.

  Monitor and debug the cluster:  
    cluster list         Lists all nodes in the MAAS Anvil cluster.  
    inspect              Inspects the MAAS Anvil cluster, will report any issues it finds and  
                         create a tarball of logs and traces.

  Manage a deployment:  
    juju-login           Logs into the Juju controller used by MAAS Anvil.

Options:  
  -q, --quiet  
  -v, --verbose  
  -h, --help             Show this message and exit.
```

---

### `maas-anvil cluster [OPTIONS] COMMAND [ARGS]...`

Creates and manages a MAAS Anvil cluster across connected nodes.

Commands:  
cluster bootstrap Initializes the cluster on the first node.  
cluster add Generates a token for a new node to join the cluster.  
cluster join Joins the node to a MAAS Anvil cluster when given a valid join  
token.  
cluster list Lists all nodes in the MAAS Anvil cluster.

Options:  
 \-q, \--quiet  
 \-v, \--verbose  
 \-h, \--help Show this message and exit.

##### Example

Run the cluster bootstrap command to initialize the cluster with the first node.  
 `maas-anvil cluster bootstrap --role database --role region --role agent --role haproxy --accept-defaults`

Once the cluster is bootstrapped you can join additional nodes by running  
`maas-anvil cluster add` on the local node and  
`maas-anvil cluster join` on the joining nodes.

---

#### `maas-anvil cluster bootstrap [OPTIONS]`

Bootstraps the first node to initialize a MAAS Anvil cluster deployment.

Options:  
 \-a, \--accept-defaults Bootstraps the cluster with default configuration. Read more about  
defaults in the docs.  
 \-m, \--manifest If provided, the cluster is bootstrapped with the configuration  
 specified in the manifest file. Read more about the manifest file in  
 the docs.  
 \--role Specifies the roles for the bootstrap node. Defaults to the database  
 role. Use multiple \--role flags to assign more than one role.  
 \-h, \--help Show this message and exit.

##### Example

Bootstrap a new cluster with all available roles and default configurations on the first node. `maas-anvil cluster bootstrap --role database --role region --role agent --role haproxy --accept-defaults`

---

#### `maas-anvil cluster add [OPTIONS]`

Generates a token for a new node to join the cluster. Needs to be run on the node where the cluster was bootstrapped.

Options:  
 \--fqdn The fully qualified node name (FQDN) of the joining node.  
 \-f, \--format Output format of the join token.  
 \-h, \--help Show this message and exit.

##### Example

Add an additional node to the cluster (run this command on the bootstrap node)  
`maas-anvil cluster add --fqdn infra2.`

---

#### `maas-anvil cluster join [OPTIONS]`

Joins the node to a MAAS Anvil cluster when given a valid join token. Needs to be run on the joining node.

Options:  
 \-a, \--accept-defaults Joins the cluster with default configuration. Read more about  
defaults in the docs.  
 \--token The join token generated on the bootstrap node with `cluster`  
 `add`  
 \--role Specifies the roles for the joining node. Use multiple \--role flags to  
assign more than one role  
 \-h, \--help Show this message and exit.

##### Example

Join an additional node to the MAAS Anvil cluster. Run this command on the joining node and use the token previously created with `maas-anvil cluster add` on the bootstrap node.  
`maas-anvil cluster join --role database --role region --role agent --role haproxy --token $JOINTOKEN`

---

#### `maas-anvil cluster list [OPTIONS]`

Lists all nodes in the MAAS Anvil cluster. Can be run on any node that is connected to an active MAAS Anvil cluster.

Options:  
 \-f, \--format Output format of the list.  
 \-h, \--help Show this message and exit.

##### Example

Verify the status of your MAAS Anvil cluster.  
`maas-anvil cluster list`

---

#### `maas-anvil cluster remove [OPTIONS]`

Removes a node from the MAAS Anvil cluster. Needs to be run on the bootstrap node.

Options:  
 \--fqdn The fully qualified node name (FQDN) of the leaving node.  
 \-h, \--help Show this message and exit.

##### Example

Remove a node from the cluster. Run this command on the bootstrap node.  
`maas-anvil cluster remove --fqdn infra2.`

---

### `maas-anvil inspect`

Inspects the MAAS Anvil cluster, will report any issues it finds and create a tarball of logs and traces. You can attach this tarball to an issue filed in the MAAS Anvil Github repository.

Options:  
 \-h, \--help Show this message and exit.

##### Example

Inspect the MAAS Anvil cluster.  
`maas-anvil inspect`

---

### `maas-anvil juju-login`

Logs into the Juju controller used by MAAS Anvil with the current host user.

Options:  
 \-h, \--help Show this message and exit.

##### Example

Log into the Juju controller to manually interact with the Juju controller created by MAAS Anvil.  
`maas-anvil juju-login`

---

### `maas-anvil manifest [OPTIONS] COMMAND [ARGS]...`

Generates and manages manifest files. A manifest file is a declarative YAML file with which configurations for a MAAS Anvil cluster deployment can be set. To learn more about how to use manifest files read the docs. The manifest commands are read only.

Commands:  
manifest generate Generates a manifest file with which a MAAS Anvil deployment can  
be configured.  
manifest list Lists the currently active manifest file.  
manifest show Shows the manifest data.

Options:  
 \-h, \--help Show this message and exit.

##### Example

Generate a manifest file with (default) configuration to be saved in the default location of `$HOME/.config/anvil/manifest.yaml`  
`maas-anvil manifest generate`

---

### `maas-anvil manifest generate [OPTIONS]`

Generates a manifest file either with the configuration of the currently deployed MAAS Anvil cluster or, if no cluster was bootstrapped yet, a default configuration.

Options:  
 \-o, \--output Output file for the manifest, defaults to  
$HOME/.config/anvil/manifest.yaml  
 \-h, \--help Show this message and exit.

##### Example

Generate a manifest file with (default) configuration to be saved in the default location of `$HOME/.config/anvil/manifest.yaml`  
`maas-anvil manifest generate`

---

### `maas-anvil manifest list [OPTIONS]`

Lists all manifest files that were used in the past to create or refresh a cluster.

Options:  
 \-f, \--format Output format of the list.  
 \-h, \--help Show this message and exit.

##### Example

List previously used manifest files.  
`maas-anvil manifest list`

---

### `maas-anvil manifest show [OPTIONS]`

Shows the contents of a manifest file given an id. Get ids using the ‘manifest list’ command. Use '--id=latest' to show the most recently committed manifest.

Options:  
 \--id The database id of the manifest file  
 \-h, \--help Show this message and exit.

##### Example

Show the contents of the most recently committed manifest file.  
`maas-anvil manifest show --id=latest`

---

### `maas-anvil prepare-node-script [OPTIONS]`

Generates a script to prepare the node for use with MAAS Anvil. This must be run on every node on which you want to use MAAS Anvil.

Options:  
 \-h, \--help Show this message and exit.

##### Example

Prepare a node for usage with MAAS Anvil by generating the `prepare-node-script` and running it immediately by piping it to bash.  
`maas-anvil prepare-node-script | bash -x`

---

### `maas-anvil refresh [OPTIONS]`

Updates all charms within their current channel. A manifest file can be passed to refresh the deployment with new configuration.

Options:  
 \-m, \--manifest If provided, the cluster is refreshed with the configuration specified  
 in the manifest file. Read more about the manifest file in the [docs](http://a).  
 If ‘--manifest’ is passed, then the manifest is loaded from stdin.  
 \-u, \--upgrade-release Allows charm upgrades if the new manifest specifies charms in  
channels with higher tracks than the current one.  
 \-h, \--help Show this message and exit.

##### Example

Refresh the MAAS Anvil cluster Try: `maas-anvil refresh`
