# Copyright (c) 2024 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
from pathlib import Path
from typing import List

import click
from rich.console import Console
from rich.table import Table
from snaphelpers import Snap
from sunbeam import utils

# from sunbeam.commands import refresh as refresh_cmds
from sunbeam.commands.clusterd import (
    ClusterAddJujuUserStep,
    ClusterAddNodeStep,
    ClusterInitStep,
    ClusterJoinNodeStep,
    ClusterListNodeStep,
    ClusterRemoveNodeStep,
    ClusterUpdateJujuControllerStep,
    ClusterUpdateNodeStep,
)
from sunbeam.commands.juju import (
    AddCloudJujuStep,
    AddJujuMachineStep,
    BackupBootstrapUserStep,
    BootstrapJujuStep,
    CreateJujuUserStep,
    JujuLoginStep,
    RegisterJujuUserStep,
    RemoveJujuMachineStep,
    SaveJujuUserLocallyStep,
)
from sunbeam.jobs.checks import (
    JujuSnapCheck,
    LocalShareCheck,
    SshKeysConnectedCheck,
    TokenCheck,
    VerifyFQDNCheck,
)
from sunbeam.jobs.common import (
    CONTEXT_SETTINGS,
    FORMAT_DEFAULT,
    FORMAT_TABLE,
    FORMAT_VALUE,
    FORMAT_YAML,
    ResultType,
    get_step_message,
    run_plan,
    run_preflight_checks,
)
from sunbeam.jobs.deployment import Deployment
from sunbeam.jobs.juju import JujuHelper
from sunbeam.jobs.manifest import AddManifestStep
from sunbeam.provider.base import ProviderBase
from sunbeam.provider.local.deployment import LOCAL_TYPE
import yaml

from anvil.commands.haproxy import (
    RemoveHAProxyUnitStep,
    haproxy_install_steps,
)
from anvil.commands.juju import JujuAddSSHKeyStep, ScaleJujuStep
from anvil.commands.maas_agent import (
    RemoveMAASAgentUnitStep,
    maas_agent_install_steps,
)
from anvil.commands.maas_region import (
    RemoveMAASRegionUnitStep,
    maas_region_install_steps,
)
from anvil.commands.postgresql import (
    ReapplyPostgreSQLTerraformPlanStep,
    RemovePostgreSQLUnitStep,
    postgresql_install_steps,
)
from anvil.jobs.checks import DaemonGroupCheck, SystemRequirementsCheck
from anvil.jobs.common import (
    Role,
    roles_to_str_list,
    validate_roles,
)
from anvil.jobs.juju import CONTROLLER
from anvil.jobs.manifest import Manifest
from anvil.provider.local.deployment import LocalDeployment
from anvil.utils import CatchGroup

LOG = logging.getLogger(__name__)
console = Console()


@click.group("cluster", context_settings=CONTEXT_SETTINGS, cls=CatchGroup)
@click.pass_context
def cluster(ctx: click.Context) -> None:
    """Manage the MAAS Cluster"""


def remove_trailing_dot(value: str) -> str:
    """Remove trailing dot from the value."""
    return value.rstrip(".")


class LocalProvider(ProviderBase):
    def register_add_cli(self, add: click.Group) -> None:
        """A local provider cannot add deployments."""
        pass

    def register_cli(
        self,
        init: click.Group,
        configure: click.Group,
        deployment: click.Group,
    ) -> None:
        """Register local provider commands to CLI.

        Local provider does not add commands to the deployment group.
        """
        init.add_command(cluster)
        cluster.add_command(bootstrap)
        cluster.add_command(add)
        cluster.add_command(join)
        cluster.add_command(list)
        cluster.add_command(remove)
        # cluster.add_command(refresh_cmds.refresh)

    def deployment_type(self) -> tuple[str, type[Deployment]]:
        return LOCAL_TYPE, LocalDeployment


@click.command()
@click.option(
    "-a", "--accept-defaults", help="Accept all defaults.", is_flag=True
)
@click.option(
    "-m",
    "--manifest",
    help="Manifest file.",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--role",
    "roles",
    multiple=True,
    default=["database"],
    type=click.Choice(
        ["region", "agent", "database", "haproxy"], case_sensitive=False
    ),
    callback=validate_roles,
    help="Specify additional roles, region or agent, for the "
    "bootstrap node. Defaults to the database role.",
)
@click.pass_context
def bootstrap(
    ctx: click.Context,
    roles: List[Role],
    manifest: Path | None = None,
    accept_defaults: bool = False,
) -> None:
    """Bootstrap the local node.

    Initialize the MAAS cluster.
    """
    deployment: LocalDeployment = ctx.obj
    client = deployment.get_client()
    snap = Snap()

    # Validate manifest file
    manifest_obj = None
    if manifest:
        manifest_obj = Manifest.load(
            deployment, manifest_file=manifest, include_defaults=True
        )
    else:
        manifest_obj = Manifest.get_default_manifest(deployment)

    LOG.debug(
        f"Manifest used for deployment - preseed: {manifest_obj.deployment_config}"
    )
    LOG.debug(
        f"Manifest used for deployment - software: {manifest_obj.software_config}"
    )
    preseed = manifest_obj.deployment_config

    # Bootstrap node must always have the database role
    if Role.DATABASE not in roles:
        LOG.debug("Enabling database role for bootstrap")
        roles.append(Role.DATABASE)
    is_region_node = any(role.is_region_node() for role in roles)
    is_agent_node = any(role.is_agent_node() for role in roles)
    is_haproxy_node = any(role.is_haproxy_node() for role in roles)

    fqdn = utils.get_fqdn()

    roles_str = ",".join(role.name for role in roles)
    pretty_roles = ", ".join(role.name.lower() for role in roles)
    LOG.debug(f"Bootstrap node: roles {roles_str}")

    cloud_type = snap.config.get("juju.cloud.type")
    cloud_name = snap.config.get("juju.cloud.name")
    cloud_definition = JujuHelper.manual_cloud(
        cloud_name, utils.get_local_ip_by_default_route()
    )
    juju_bootstrap_args = manifest_obj.software_config.juju.bootstrap_args  # type: ignore[union-attr]
    data_location = snap.paths.user_data

    preflight_checks = [
        SystemRequirementsCheck(),
        JujuSnapCheck(),
        SshKeysConnectedCheck(),
        DaemonGroupCheck(),
        LocalShareCheck(),
    ]
    run_preflight_checks(preflight_checks, console)

    plan = [
        JujuLoginStep(deployment.juju_account),
        ClusterInitStep(
            client, roles_to_str_list(roles), 0
        ),  # bootstrapped node is always machine 0 in controller model
        AddManifestStep(client, manifest) if manifest else None,
        AddCloudJujuStep(cloud_name, cloud_definition),
        BootstrapJujuStep(
            client,
            cloud_name,
            cloud_type,
            CONTROLLER,
            bootstrap_args=juju_bootstrap_args,
            deployment_preseed=preseed,
            accept_defaults=accept_defaults,
        ),
    ]
    run_plan(filter(None, plan), console)

    plan2 = [
        CreateJujuUserStep(fqdn),
        ClusterUpdateJujuControllerStep(client, CONTROLLER),
    ]
    plan2_results = run_plan(plan2, console)
    token = get_step_message(plan2_results, CreateJujuUserStep)

    plan3 = [
        ClusterAddJujuUserStep(client, fqdn, token),
        BackupBootstrapUserStep(fqdn, data_location),
        SaveJujuUserLocallyStep(fqdn, data_location),
        RegisterJujuUserStep(
            client, fqdn, CONTROLLER, data_location, replace=True
        ),
    ]
    run_plan(plan3, console)

    deployment.reload_juju_credentials()
    jhelper = JujuHelper(deployment.get_connected_controller())

    plan4 = postgresql_install_steps(
        client,
        manifest_obj,
        jhelper,
        deployment.infrastructure_model,
        fqdn,
        accept_defaults,
        preseed,
    )
    if is_haproxy_node:
        plan4.extend(
            haproxy_install_steps(
                client,
                manifest_obj,
                jhelper,
                deployment.infrastructure_model,
                fqdn,
                accept_defaults,
                preseed,
            )
        )
    if is_region_node:
        plan4.extend(
            maas_region_install_steps(
                client,
                manifest_obj,
                jhelper,
                deployment.infrastructure_model,
                fqdn,
            )
        )
    if is_agent_node:
        plan4.extend(
            maas_agent_install_steps(
                client,
                manifest_obj,
                jhelper,
                deployment.infrastructure_model,
                fqdn,
            )
        )
    run_plan(plan4, console)

    click.echo(f"Node has been bootstrapped with roles: {pretty_roles}")


@click.command()
@click.option(
    "--name",
    type=str,
    prompt=True,
    help="Fully qualified node name",
)
@click.option(
    "-f",
    "--format",
    type=click.Choice([FORMAT_DEFAULT, FORMAT_VALUE, FORMAT_YAML]),
    default=FORMAT_DEFAULT,
    help="Output format.",
)
@click.pass_context
def add(ctx: click.Context, name: str, format: str) -> None:
    """Generate a token for a new node to join the cluster."""
    preflight_checks = [DaemonGroupCheck(), VerifyFQDNCheck(name)]
    run_preflight_checks(preflight_checks, console)
    name = remove_trailing_dot(name)

    deployment: LocalDeployment = ctx.obj
    client = deployment.get_client()

    plan1 = [
        JujuLoginStep(deployment.juju_account),
        ClusterAddNodeStep(client, name),
        CreateJujuUserStep(name),
    ]

    plan1_results = run_plan(plan1, console)

    user_token = get_step_message(plan1_results, CreateJujuUserStep)

    plan2 = [ClusterAddJujuUserStep(client, name, user_token)]
    run_plan(plan2, console)

    def _print_output(token: str) -> None:
        """Helper for printing formatted output."""
        if format == FORMAT_DEFAULT:
            console.print(
                f"Token for the Node {name}: {token}", soft_wrap=True
            )
        elif format == FORMAT_YAML:
            click.echo(yaml.dump({"token": token}))
        elif format == FORMAT_VALUE:
            click.echo(token)

    add_node_step_result = plan1_results.get("ClusterAddNodeStep")
    if add_node_step_result.result_type == ResultType.COMPLETED:
        _print_output(add_node_step_result.message)
    elif add_node_step_result.result_type == ResultType.SKIPPED:
        if add_node_step_result.message:
            _print_output(add_node_step_result.message)
        else:
            console.print("Node already a member of the MAAS cluster")


@click.command()
@click.option(
    "-a", "--accept-defaults", help="Accept all defaults.", is_flag=True
)
@click.option("--token", type=str, help="Join token")
@click.option(
    "--role",
    "roles",
    multiple=True,
    default=["region"],
    type=click.Choice(
        ["region", "agent", "database", "haproxy"], case_sensitive=False
    ),
    callback=validate_roles,
    help="Specify which roles the node will be assigned in the cluster.",
)
@click.pass_context
def join(
    ctx: click.Context,
    token: str,
    roles: List[Role],
    accept_defaults: bool = False,
) -> None:
    """Join node to the cluster.

    Join the node to the cluster.
    """
    is_region_node = any(role.is_region_node() for role in roles)
    is_agent_node = any(role.is_agent_node() for role in roles)
    is_database_node = any(role.is_database_node() for role in roles)
    is_haproxy_node = any(role.is_haproxy_node() for role in roles)

    # Register Juju user with same name as Node fqdn
    name = utils.get_fqdn()
    ip = utils.get_local_ip_by_default_route()

    roles_str = roles_to_str_list(roles)
    pretty_roles = ", ".join(role_.name.lower() for role_ in roles)
    LOG.debug(f"Node joining the cluster with roles: {pretty_roles}")

    preflight_checks = [
        SystemRequirementsCheck(),
        JujuSnapCheck(),
        SshKeysConnectedCheck(),
        DaemonGroupCheck(),
        LocalShareCheck(),
        TokenCheck(name, token),
    ]
    run_preflight_checks(preflight_checks, console)

    controller = CONTROLLER
    deployment: LocalDeployment = ctx.obj
    data_location = Snap().paths.user_data
    client = deployment.get_client()

    plan1 = [
        JujuLoginStep(deployment.juju_account),
        ClusterJoinNodeStep(client, token, roles_str),
        SaveJujuUserLocallyStep(name, data_location),
        RegisterJujuUserStep(client, name, controller, data_location),
        AddJujuMachineStep(ip),
        JujuAddSSHKeyStep(),
    ]
    plan1_results = run_plan(plan1, console)

    deployment.reload_juju_credentials()

    # Get manifest object once the cluster is joined
    manifest_obj = Manifest.load_latest_from_clusterdb(
        deployment, include_defaults=True
    )
    preseed = manifest_obj.deployment_config

    machine_id = -1
    machine_id_result = get_step_message(plan1_results, AddJujuMachineStep)
    if machine_id_result is not None:
        machine_id = int(machine_id_result)

    jhelper = JujuHelper(deployment.get_connected_controller())
    plan2 = [ClusterUpdateNodeStep(client, name, machine_id=machine_id)]

    if is_database_node:
        plan2.extend(
            postgresql_install_steps(
                client,
                manifest_obj,
                jhelper,
                deployment.infrastructure_model,
                name,
                accept_defaults,
                preseed,
            )
        )
    if is_haproxy_node:
        plan2.extend(
            haproxy_install_steps(
                client,
                manifest_obj,
                jhelper,
                deployment.infrastructure_model,
                name,
                accept_defaults,
                preseed,
            )
        )
    if is_region_node:
        plan2.extend(
            maas_region_install_steps(
                client,
                manifest_obj,
                jhelper,
                deployment.infrastructure_model,
                name,
            )
        )
        plan2.append(
            ReapplyPostgreSQLTerraformPlanStep(
                client, manifest_obj, jhelper, deployment.infrastructure_model
            )
        )
    if is_agent_node:
        plan2.extend(
            maas_agent_install_steps(
                client,
                manifest_obj,
                jhelper,
                deployment.infrastructure_model,
                name,
            )
        )
    plan2.append(ScaleJujuStep(jhelper, deployment.infrastructure_model))
    run_plan(plan2, console)

    click.echo(f"Node joined cluster with roles: {pretty_roles}")


@click.command()
@click.option(
    "-f",
    "--format",
    type=click.Choice([FORMAT_TABLE, FORMAT_YAML]),
    default=FORMAT_TABLE,
    help="Output format.",
)
@click.pass_context
def list(ctx: click.Context, format: str) -> None:
    """List nodes in the cluster."""
    preflight_checks = [DaemonGroupCheck()]
    run_preflight_checks(preflight_checks, console)
    deployment: LocalDeployment = ctx.obj
    client = deployment.get_client()
    plan = [ClusterListNodeStep(client)]
    results = run_plan(plan, console)

    list_node_step_result = results.get("ClusterListNodeStep")
    nodes = list_node_step_result.message

    if format == FORMAT_TABLE:
        table = Table()
        table.add_column("Node", justify="left")
        table.add_column("Status", justify="center")
        table.add_column("Region", justify="center")
        table.add_column("Agent", justify="center")
        table.add_column("Database", justify="center")
        table.add_column("HAProxy", justify="center")
        for name, node in nodes.items():
            table.add_row(
                name,
                (
                    "[green]up[/green]"
                    if node.get("status") == "ONLINE"
                    else "[red]down[/red]"
                ),
                "x" if "region" in node.get("roles", []) else "",
                "x" if "agent" in node.get("roles", []) else "",
                "x" if "database" in node.get("roles", []) else "",
                "x" if "haproxy" in node.get("roles", []) else "",
            )
        console.print(table)
    elif format == FORMAT_YAML:
        click.echo(yaml.dump(nodes, sort_keys=True))


@click.command()
@click.option(
    "--name", type=str, prompt=True, help="Fully qualified node name"
)
@click.pass_context
def remove(ctx: click.Context, name: str) -> None:
    """Remove a node from the cluster."""
    deployment: LocalDeployment = ctx.obj
    client = deployment.get_client()
    jhelper = JujuHelper(deployment.get_connected_controller())

    preflight_checks = [DaemonGroupCheck()]
    run_preflight_checks(preflight_checks, console)

    manifest_obj = Manifest.load_latest_from_clusterdb(
        deployment, include_defaults=True
    )

    plan = [
        JujuLoginStep(deployment.juju_account),
        RemovePostgreSQLUnitStep(
            client, name, jhelper, deployment.infrastructure_model
        ),
        RemoveHAProxyUnitStep(
            client, name, jhelper, deployment.infrastructure_model
        ),
        RemoveMAASRegionUnitStep(
            client, name, jhelper, deployment.infrastructure_model
        ),
        ReapplyPostgreSQLTerraformPlanStep(
            client, manifest_obj, jhelper, deployment.infrastructure_model
        ),
        RemoveMAASAgentUnitStep(
            client, name, jhelper, deployment.infrastructure_model
        ),
        RemoveJujuMachineStep(client, name),
        # Cannot remove user as the same user name cannot be reused,
        # so commenting the RemoveJujuUserStep
        # RemoveJujuUserStep(name),
        ScaleJujuStep(jhelper, deployment.infrastructure_model),
        ClusterRemoveNodeStep(client, name),
    ]
    run_plan(plan, console)
    click.echo(f"Removed node {name} from the cluster")
    # Removing machine does not clean up all deployed Juju components. This is
    # deliberate, see https://bugs.launchpad.net/juju/+bug/1851489.
    # Without the workaround mentioned in LP#1851489, it is not possible to
    # reprovision the machine back.
    click.echo(
        f"Run command 'sudo /sbin/remove-juju-services' on node {name} "
        "to reuse the machine."
    )
