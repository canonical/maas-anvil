import logging
from pathlib import Path

import click
from rich.console import Console
from rich.status import Status
from sunbeam.clusterd.client import Client
from sunbeam.commands.juju import JujuStepHelper
from sunbeam.commands.upgrades.base import UpgradePlugins
from sunbeam.jobs.common import (
    BaseStep,
    Result,
    ResultType,
    run_plan,
)
from sunbeam.jobs.deployment import Deployment
from sunbeam.jobs.juju import JujuHelper, run_sync

from anvil.commands.haproxy import (
    UpgradeHAProxyUnitCharms,
    haproxy_upgrade_steps,
)
from anvil.commands.maas_agent import (
    UpgradeMAASAgentUnitCharms,
    maas_agent_upgrade_steps,
)
from anvil.commands.maas_region import (
    UpgradeMAASRegionUnitCharms,
    maas_region_upgrade_steps,
)
from anvil.commands.postgresql import (
    UpgradePostgreSQLUnitCharms,
    postgresql_upgrade_steps,
)
from anvil.jobs.manifest import Manifest
from anvil.provider.local.deployment import LocalDeployment

LOG = logging.getLogger(__name__)
console = Console()


# We reimplement from sunbeam to avoid openstack dependencies
class LatestInChannel(BaseStep, JujuStepHelper):
    def __init__(self, jhelper: JujuHelper, manifest: Manifest):
        """Upgrade all charms to latest in current channel."""
        super().__init__(
            "In channel upgrade",
            "Upgrade charms to latest revision in current channel",
        )
        self.jhelper = jhelper
        self.manifest = manifest

    def is_skip(self, status: Status | None = None) -> Result:
        """Step can be skipped if nothing needs refreshing."""
        return Result(ResultType.COMPLETED)

    def is_track_changed_for_any_charm(
        self, deployed_apps: dict[str, tuple[str, str, str]]
    ) -> bool:
        """Check if chanel track is same in manifest and deployed app."""
        for name, (charm, channel, revision) in deployed_apps.items():
            charm_manifest = (self.manifest.software_config.charms or {}).get(
                charm
            )
            if not charm_manifest:
                LOG.debug(f"Charm not present in manifest: {charm}")
                continue

            if (charm_manifest.channel or "").split("/")[0] != channel.split(
                "/"
            )[0]:
                LOG.debug(
                    f"Channel for {name} in manifest does not match deployed"
                )
                return True

        return False

    def refresh_apps(
        self, apps: dict[str, tuple[str, str, str]], model: str
    ) -> None:
        """Refresh apps in the model.

        If the charm has no revision in manifest and channel mentioned in manifest
        and the deployed app is same, run juju refresh.
        Otherwise ignore so that terraform plan apply will take care of charm upgrade.
        """
        for name, (charm, channel, revision) in apps.items():
            charm_manifest = (self.manifest.software_config.charms or {}).get(
                charm
            )
            if not charm_manifest:
                continue

            if (
                not charm_manifest.revision
                and charm_manifest.channel == channel
            ):
                app = run_sync(self.jhelper.get_application(name, model))
                LOG.debug(f"Running refresh for app {name}")
                run_sync(app.refresh())

    def run(self, status: Status | None = None) -> Result:
        """Refresh all charms identified as needing a refresh.

        If the manifest has charm channel and revision, terraform apply should update
        the charms.
        If the manifest has only charm, then juju refresh is required if channel is
        same as deployed charm, otherwise juju upgrade charm.
        """
        deployed_machine_apps = self.get_charm_deployed_versions("controller")

        all_deployed_apps = deployed_machine_apps.copy()
        LOG.debug(f"All deployed apps: {all_deployed_apps}")
        if self.is_track_changed_for_any_charm(all_deployed_apps):
            error_msg = "Manifest contains cross track upgrades, please re-run with `--upgrade-release`."
            return Result(ResultType.FAILED, error_msg)

        self.refresh_apps(deployed_machine_apps, "controller")
        return Result(ResultType.COMPLETED)


class LatestInChannelCoordinator:
    """Coordinator for refreshing charms in their current channel."""

    def __init__(
        self,
        deployment: Deployment,
        client: Client,
        jhelper: JujuHelper,
        manifest: Manifest,
        accept_defaults: bool = False,
    ):
        """Upgrade coordinator.

        Execute plan for conducting an upgrade.

        :client: Helper for interacting with clusterd
        :jhelper: Helper for interacting with pylibjuju
        :manifest: Manifest object
        """
        self.deployment = deployment
        self.client = client
        self.jhelper = jhelper
        self.manifest = manifest
        self.accept_defaults = accept_defaults
        self.preseed = self.manifest.deployment_config

    def get_plan(self) -> list[BaseStep]:
        """Return the upgrade plan."""
        plan: list[BaseStep] = []
        plan.append(LatestInChannel(self.jhelper, self.manifest))

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
        # plan.append(
        #     UpgradeFeatures(self.deployment, upgrade_release=False),
        # )
        plan.append(UpgradePlugins(self.deployment, upgrade_release=False))

        return plan


class ChannelUpgradeCoordinator:
    def __init__(
        self,
        deployment: Deployment,
        client: Client,
        jhelper: JujuHelper,
        manifest: Manifest,
    ):
        self.deployment = deployment
        self.client = client
        self.jhelper = jhelper
        self.manifest = manifest

    def get_plan(self) -> list[BaseStep]:
        """Return the plan for this upgrade.

        Return the steps to complete this upgrade.
        """
        plan = [
            UpgradeHAProxyUnitCharms(
                self.client,
                self.jhelper,
                self.manifest,
                self.deployment.infrastructure_model,
            ),
            UpgradePostgreSQLUnitCharms(
                self.client,
                self.jhelper,
                self.manifest,
                self.deployment.infrastructure_model,
            ),
            UpgradeMAASRegionUnitCharms(
                self.client,
                self.jhelper,
                self.manifest,
                self.deployment.infrastructure_model,
            ),
            UpgradeMAASAgentUnitCharms(
                self.client,
                self.jhelper,
                self.manifest,
                self.deployment.infrastructure_model,
            ),
            # TODO: Update MAAS-Anvil sunbeam tag to allow using
            # sunbeam.commands.upgrades.base.UpgradeFeatures instead of
            # sunbeam.commands.upgrades.base.UpgradePlugins
            # plan.append(
            #     UpgradeFeatures(self.deployment, upgrade_release=False),
            # )
            UpgradePlugins(self.deployment, upgrade_release=True),
        ]
        return plan


@click.command()
@click.option(
    "-m",
    "--manifest",
    "manifest_path",
    help="Manifest file.",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "-u",
    "--upgrade-release",
    is_flag=True,
    show_default=True,
    default=False,
    help="Upgrade MAAS-Anvil release.",
)
@click.option(
    "-a", "--accept-defaults", help="Accept all defaults.", is_flag=True
)
@click.pass_context
def refresh(
    ctx: click.Context,
    manifest_path: Path | None = None,
    upgrade_release: bool = False,
    accept_defaults: bool = False,
) -> None:
    """Refresh deployment.

    Refresh the deployment and allow passing new configuration options.
    """

    deployment: LocalDeployment = ctx.obj
    client = deployment.get_client()

    manifest = None
    if manifest_path:
        manifest = Manifest.load(
            deployment, manifest_file=manifest_path, include_defaults=True
        )
    else:
        manifest = Manifest.get_default_manifest(deployment)

    LOG.debug(
        f"Manifest used for refresh - deployment preseed: {manifest.deployment_config}"
    )
    LOG.debug(
        f"Manifest used for refresh - software: {manifest.software_config}"
    )
    jhelper = JujuHelper(deployment.get_connected_controller())

    coordinator = (
        ChannelUpgradeCoordinator(
            deployment,
            client,
            jhelper,
            manifest,
        )
        if upgrade_release
        else LatestInChannelCoordinator(
            deployment,
            client,
            jhelper,
            manifest,
            accept_defaults=accept_defaults,
        )
    )
    upgrade_plan = coordinator.get_plan()  # type:ignore [attr-defined]
    run_plan(upgrade_plan, console)

    click.echo("Refresh complete.")
