import logging
from pathlib import Path

import click
from rich.console import Console
from sunbeam.clusterd.client import Client
from sunbeam.commands.upgrades.base import (
    UpgradeCoordinator,
    UpgradePlugins,
)
from sunbeam.commands.upgrades.intra_channel import (
    LatestInChannel,
)
from sunbeam.jobs.common import (
    BaseStep,
    run_plan,
)
from sunbeam.jobs.deployment import Deployment
from sunbeam.jobs.deployments import Deployment
from sunbeam.jobs.juju import JujuHelper
from sunbeam.jobs.manifest import AddManifestStep, Manifest

from anvil.commands.haproxy import haproxy_upgrade_steps
from anvil.commands.maas_agent import maas_agent_upgrade_steps
from anvil.commands.maas_region import maas_region_upgrade_steps
from anvil.commands.postgresql import postgresql_upgrade_steps
from anvil.jobs.manifest import Manifest
from anvil.provider.local.deployment import LocalDeployment

LOG = logging.getLogger(__name__)
console = Console()


class LatestInChannelCoordinator(UpgradeCoordinator):
    """Coordinator for refreshing charms in their current channel."""

    def __init__(
        self,
        deployment: Deployment,
        client: Client,
        jhelper: JujuHelper,
        manifest: Manifest,
        accept_defaults: bool = False,
    ):
        super().__init__(deployment, client, jhelper, manifest)
        self.accept_defaults = accept_defaults
        self.preseed = self.manifest.deployment_config

    def get_plan(self) -> list[BaseStep]:
        """Return the upgrade plan."""
        plan: list[BaseStep] = [LatestInChannel(self.jhelper, self.manifest)]

        plan.extend(
            haproxy_upgrade_steps(
                self.client,
                self.manifest,
                self.jhelper,
                self.deployment.infrastructure_model,
                self.accept_defaults,
                self.preseed,
            )
        )
        plan.extend(
            postgresql_upgrade_steps(
                self.client,
                self.manifest,
                self.jhelper,
                self.deployment.infrastructure_model,
                self.accept_defaults,
                self.preseed,
            )
        )
        plan.extend(
            maas_region_upgrade_steps(
                self.client,
                self.manifest,
                self.jhelper,
                self.deployment.infrastructure_model,
            )
        )
        plan.extend(
            maas_agent_upgrade_steps(
                self.client,
                self.manifest,
                self.jhelper,
                self.deployment.infrastructure_model,
            )
        )

        # TODO: Update MAAS-Anvil sunbeam tag to allow using
        # sunbeam.commands.upgrades.base.UpgradeFeatures instead of
        # sunbeam.commands.upgrades.base.UpgradePlugins
        # plan.extend(
        #     UpgradeFeatures(self.deployment, upgrade_release=False),
        # )
        plan.extend(UpgradePlugins(self.deployment, upgrade_release=False))

        return plan


@click.command()
@click.option(
    "-c",
    "--clear-manifest",
    is_flag=True,
    default=False,
    help="Clear the manifest file.",
    type=bool,
)
@click.option(
    "-m",
    "--manifest",
    "manifest_path",
    help="Manifest file.",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--upgrade-release",
    is_flag=True,
    show_default=True,
    default=False,
    help="Upgrade OpenStack release.",
)
@click.option(
    "-a", "--accept-defaults", help="Accept all defaults.", is_flag=True
)
@click.pass_context
def refresh(
    ctx: click.Context,
    upgrade_release: bool,
    manifest_path: Path | None = None,
    clear_manifest: bool = False,
    accept_defaults: bool = False,
) -> None:
    """Refresh deployment.

    Refresh the deployment. If --upgrade-release is supplied then charms are
    upgraded the channels aligned with this snap revision
    """

    deployment: LocalDeployment = ctx.obj
    client = deployment.get_client()

    manifest = None
    if clear_manifest:
        raise click.ClickException(
            "Anvil does not currently support clear-manifest."
        )
    elif manifest_path:
        manifest = Manifest.load(
            deployment, manifest_file=manifest, include_defaults=True
        )
    else:
        manifest = Manifest.get_default_manifest(deployment)

    if not manifest:
        LOG.debug("Getting latest manifest from cluster db")
        manifest = deployment.get_manifest()

    LOG.debug(f"Manifest used for deployment - software: {manifest.software}")
    jhelper = JujuHelper(deployment.get_connected_controller())

    if upgrade_release:
        raise click.ClickException(
            "Anvil does not current support upgrade-release."
        )
    else:
        a = LatestInChannelCoordinator(
            deployment,
            client,
            jhelper,
            manifest,
            accept_defaults=accept_defaults,
        )
        a.run_plan()

    click.echo("Refresh complete.")
