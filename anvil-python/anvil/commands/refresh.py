import logging
from pathlib import Path

import click
from rich.console import Console
from sunbeam.clusterd.client import Client
from sunbeam.commands.clusterd import (
    ClusterListNodeStep,
)
from sunbeam.jobs.checks import (
    SshKeysConnectedCheck,
)
from sunbeam.jobs.common import BaseStep, run_plan, run_preflight_checks
from sunbeam.jobs.juju import JujuHelper

from anvil.commands.haproxy import UpgradeHAProxyCharm, haproxy_install_steps
from anvil.commands.maas_agent import (
    UpgradeMAASAgentCharm,
    maas_agent_install_steps,
)
from anvil.commands.maas_region import (
    UpgradeMAASRegionCharm,
    maas_region_install_steps,
)
from anvil.commands.postgresql import (
    UpgradePostgreSQLCharm,
    postgresql_install_steps,
)
from anvil.jobs.checks import DaemonGroupCheck, VerifyBootstrappedCheck
from anvil.jobs.manifest import Manifest
from anvil.provider.local.deployment import LocalDeployment

LOG = logging.getLogger(__name__)
console = Console()


def refresh_node(
    client: Client,
    name: str,
    manifest: Manifest,
    deployment: LocalDeployment,
    roles: list[str] = [],
    accept_defaults: bool = False,
) -> None:
    jhelper = JujuHelper(deployment.get_connected_controller())

    is_database_node = "database" in roles
    is_haproxy_node = "haproxy" in roles
    is_region_node = "region" in roles
    is_agent_node = "agent" in roles

    preseed = manifest.deployment_config

    plan: list[BaseStep] = []
    if is_database_node:
        plan.extend(
            postgresql_install_steps(
                client, manifest, jhelper, deployment, name, True
            )
        )
    if is_haproxy_node:
        plan.extend(
            haproxy_install_steps(
                client,
                manifest,
                jhelper,
                deployment.infrastructure_model,
                name,
                accept_defaults,
                preseed,
                refresh=True,
            )
        )
    if is_region_node:
        plan.extend(
            maas_region_install_steps(
                client, manifest, jhelper, deployment, name, refresh=True
            )
        )
    if is_agent_node:
        plan.extend(
            maas_agent_install_steps(
                client, manifest, jhelper, deployment, name, refresh=True
            )
        )
    run_plan(plan, console)

    click.echo(f"Node {name} has been refreshed")


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
    "--upgrade",
    is_flag=True,
    show_default=True,
    default=False,
    help="Upgrade release.",
)
@click.pass_context
def refresh(
    ctx: click.Context,
    manifest: Path | None = None,
    accept_defaults: bool = False,
    upgrade: bool = False,
) -> None:
    """Refresh the anvil cluster."""

    deployment: LocalDeployment = ctx.obj
    client = deployment.get_client()
    run_preflight_checks(
        [
            SshKeysConnectedCheck(),
            VerifyBootstrappedCheck(),
            DaemonGroupCheck(),
        ],
        console,
    )

    manifest_obj = (
        Manifest.load(
            deployment, manifest_file=manifest, include_defaults=True
        )
        if manifest
        else Manifest.get_default_manifest(deployment)
    )

    nodes = (
        run_plan([ClusterListNodeStep(client)], console)
        .get("ClusterListNodeStep")
        .message
    )

    for name, node in nodes.items():
        refresh_node(
            client,
            name,
            manifest_obj,
            deployment,
            node.get("roles", []),
            accept_defaults=accept_defaults,
        )

    if upgrade:
        jhelper = JujuHelper(deployment.get_connected_controller())
        upgrade_plan = [
            UpgradePostgreSQLCharm(
                client, jhelper, manifest, deployment.infrastructure_model
            ),
            UpgradeHAProxyCharm(
                client, jhelper, manifest, deployment.infrastructure_model
            ),
            UpgradeMAASRegionCharm(
                client, jhelper, manifest, deployment.infrastructure_model
            ),
            UpgradeMAASAgentCharm(
                client, jhelper, manifest, deployment.infrastructure_model
            ),
        ]
        run_plan(upgrade_plan, console)
