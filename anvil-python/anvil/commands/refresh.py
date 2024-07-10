import logging
from pathlib import Path

import click
from rich.console import Console
from sunbeam import utils
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
from sunbeam.jobs.checks import (
    SshKeysConnectedCheck,
)
from sunbeam.jobs.common import BaseStep, run_plan, run_preflight_checks
from sunbeam.jobs.juju import JujuHelper

from anvil.commands.haproxy import (
    haproxy_install_steps,
)
from anvil.commands.maas_agent import (
    maas_agent_install_steps,
)
from anvil.commands.maas_region import (
    maas_region_install_steps,
)
from anvil.commands.postgresql import (
    postgresql_install_steps,
)
from anvil.jobs.checks import VerifyBootstrappedCheck
from anvil.jobs.manifest import Manifest
from anvil.provider.local.deployment import LocalDeployment

LOG = logging.getLogger(__name__)
console = Console()


@click.command()
@click.pass_context
def refresh(ctx: click.Context, manifest: Path | None = None) -> None:
    """Refresh anvil cluster."""

    deployment: LocalDeployment = ctx.obj
    client = deployment.get_client()

    manifest_obj = (
        Manifest.load(
            deployment, manifest_file=manifest, include_defaults=True
        )
        if manifest
        else Manifest.get_default_manifest(deployment)
    )
    preseed = manifest_obj.deployment_config

    # Don't refresh a cluster that isn't bootstrapped
    preflight_checks = [SshKeysConnectedCheck(), VerifyBootstrappedCheck()]
    run_preflight_checks(preflight_checks, console)

    jhelper = JujuHelper(deployment.get_connected_controller())
    fqdn = utils.get_fqdn()

    roles = client.cluster.get_node_info(fqdn).get("roles", [])
    is_database_node = "database" in roles
    is_haproxy_node = "haproxy" in roles
    is_region_node = "region" in roles
    is_agent_node = "agent" in roles

    plan: list[BaseStep] = []
    if is_database_node:
        plan.extend(
            postgresql_install_steps(
                client, manifest_obj, jhelper, deployment, fqdn, True
            )
        )
    if is_haproxy_node:
        plan.extend(
            haproxy_install_steps(
                client,
                manifest_obj,
                jhelper,
                deployment.infrastructure_model,
                fqdn,
                True,
                preseed,
                refresh=True,
            )
        )
    if is_region_node:
        plan.extend(
            maas_region_install_steps(
                client, manifest_obj, jhelper, deployment, fqdn, refresh=True
            )
        )
    if is_agent_node:
        plan.extend(
            maas_agent_install_steps(
                client, manifest_obj, jhelper, deployment, fqdn, refresh=True
            )
        )
    run_plan(plan, console)
