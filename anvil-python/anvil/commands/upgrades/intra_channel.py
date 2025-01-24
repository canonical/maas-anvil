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

from rich.console import Console
from rich.status import Status
from sunbeam.clusterd.client import Client
from sunbeam.commands.juju import JujuStepHelper
from sunbeam.jobs.common import (
    BaseStep,
    Result,
    ResultType,
    run_plan,
)
from sunbeam.jobs.deployment import Deployment
from sunbeam.jobs.juju import JujuHelper, run_sync

from anvil.commands.haproxy import haproxy_upgrade_steps
from anvil.commands.maas_agent import maas_agent_upgrade_steps
from anvil.commands.maas_region import maas_region_upgrade_steps
from anvil.commands.postgresql import postgresql_upgrade_steps
from anvil.commands.upgrades.base import (
    UpgradePlugins,
)
from anvil.jobs.manifest import Manifest

LOG = logging.getLogger(__name__)
console = Console()


class LatestInChannel(BaseStep, JujuStepHelper):
    def __init__(self, jhelper: JujuHelper, manifest: Manifest):
        """Upgrade all charms to latest in current channel.

        :jhelper: Helper for interacting with pylibjuju
        """
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
        self.preseed = self.manifest.deployment_config

    def run_plan(self) -> None:
        """Execute the upgrade plan."""
        plan = self.get_plan()
        run_plan(plan, console)

    def get_plan(self) -> list[BaseStep]:
        """Return the upgrade plan."""
        plan: list[BaseStep] = []
        plan.append(LatestInChannel(self.jhelper, self.manifest))
        plan.extend(
            postgresql_upgrade_steps(
                self.client,
                self.manifest,
                self.jhelper,
                self.deployment.infrastructure_model,
                self.preseed,
            )
        )

        if self.client.cluster.list_nodes_by_role("haproxy"):
            plan.extend(
                haproxy_upgrade_steps(
                    self.client,
                    self.manifest,
                    self.jhelper,
                    self.deployment.infrastructure_model,
                    self.preseed,
                )
            )
        if self.client.cluster.list_nodes_by_role("region"):
            plan.extend(
                maas_region_upgrade_steps(
                    self.client,
                    self.manifest,
                    self.jhelper,
                    self.deployment.infrastructure_model,
                    self.preseed,
                )
            )
        if self.client.cluster.list_nodes_by_role("agent"):
            plan.extend(
                maas_agent_upgrade_steps(
                    self.client,
                    self.manifest,
                    self.jhelper,
                    self.deployment.infrastructure_model,
                )
            )

        plan.append(UpgradePlugins(self.deployment, upgrade_release=False))

        return plan
