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
from sunbeam.commands.terraform import TerraformException
from sunbeam.jobs.common import (
    BaseStep,
    Result,
    ResultType,
    update_status_background,
)
from sunbeam.jobs.deployment import Deployment
from sunbeam.jobs.juju import (
    JujuHelper,
    JujuWaitException,
    TimeoutException,
    run_sync,
)

from anvil.commands.haproxy import (
    CONFIG_KEY as HAPROXY_CONFIG_KEY,
    HAPROXY_UNIT_TIMEOUT,
)
from anvil.commands.maas_agent import (
    CONFIG_KEY as MAASAGENT_CONFIG_KEY,
    MAASAGENT_UNIT_TIMEOUT,
)
from anvil.commands.maas_region import (
    CONFIG_KEY as MAASREGION_CONFIG_KEY,
    MAASREGION_UNIT_TIMEOUT,
)
from anvil.commands.postgresql import (
    CONFIG_KEY as POSTGRESQL_CONFIG_KEY,
    POSTGRESQL_UNIT_TIMEOUT,
)
from anvil.commands.upgrades.base import (
    UpgradePlugins,
)
from anvil.jobs.manifest import Manifest

LOG = logging.getLogger(__name__)
console = Console()


class UpgradeCharm(BaseStep, JujuStepHelper):
    def __init__(
        self,
        name: str,
        description: str,
        client: Client,
        jhelper: JujuHelper,
        manifest: Manifest,
        model: str,
        charms: list[str],
        tfplan: str,
        config: str,
        timeout: int,
    ):
        super().__init__(name, description)
        self.client = client
        self.jhelper = jhelper
        self.manifest = manifest
        self.model = model
        self.charms = charms
        self.tfplan = tfplan
        self.config = config
        self.timeout = timeout

    def run(self, status: Status | None = None) -> Result:
        """Run machine charm upgrade."""
        apps = self.get_apps_filter_by_charms(self.model, self.charms)
        result = self.upgrade_applications(
            apps,
            self.charms,
            self.model,
            self.tfplan,
            self.config,
            self.timeout,
            status,
        )
        return result

    def upgrade_applications(
        self,
        apps: list[str],
        charms: list[str],
        model: str,
        tfplan: str,
        config: str,
        timeout: int,
        status: Status | None = None,
    ) -> Result:
        expected_wls = ["active", "blocked", "unknown"]
        LOG.debug(
            f"Upgrading applications using Terraform plan {tfplan}: {apps}"
        )
        try:
            self.manifest.update_partial_tfvars_and_apply_tf(
                self.client, charms, tfplan, config
            )
        except TerraformException as e:
            LOG.exception("Error upgrading cloud")
            return Result(ResultType.FAILED, str(e))

        task = run_sync(update_status_background(self, apps, status))
        try:
            run_sync(
                self.jhelper.wait_until_desired_status(
                    model,
                    apps,
                    expected_wls,
                    timeout=timeout,
                )
            )
        except (JujuWaitException, TimeoutException) as e:
            LOG.debug(str(e))
            return Result(ResultType.FAILED, str(e))
        finally:
            if not task.done():
                task.cancel()

        return Result(ResultType.COMPLETED)


class UpgradeHAProxyCharm(UpgradeCharm):
    def __init__(
        self,
        client: Client,
        jhelper: JujuHelper,
        manifest: Manifest,
        model: str,
    ):
        super().__init__(
            "Upgrade HAProxy charm",
            "Upgrading HAProxy charm.",
            client,
            jhelper,
            manifest,
            model,
            ["haproxy", "keepalived"],
            "haproxy-plan",
            HAPROXY_CONFIG_KEY,
            HAPROXY_UNIT_TIMEOUT,
        )


class UpgradeMAASAgentCharm(UpgradeCharm):
    def __init__(
        self,
        client: Client,
        jhelper: JujuHelper,
        manifest: Manifest,
        model: str,
    ):
        super().__init__(
            "Upgrade MAAS Agent charm",
            "Upgrading MAAS Agent charm.",
            client,
            jhelper,
            manifest,
            model,
            ["maas-agent"],
            "maas-agent-plan",
            MAASAGENT_CONFIG_KEY,
            MAASAGENT_UNIT_TIMEOUT,
        )


class UpgradeMAASRegionCharm(UpgradeCharm):
    def __init__(
        self,
        client: Client,
        jhelper: JujuHelper,
        manifest: Manifest,
        model: str,
    ):
        super().__init__(
            "Upgrade MAAS Region charm",
            "Upgrading MAAS Region charm.",
            client,
            jhelper,
            manifest,
            model,
            ["maas-region"],
            "maas-region-plan",
            MAASREGION_CONFIG_KEY,
            MAASREGION_UNIT_TIMEOUT,
        )


class UpgradePostgreSQLCharm(UpgradeCharm):
    def __init__(
        self,
        client: Client,
        jhelper: JujuHelper,
        manifest: Manifest,
        model: str,
    ):
        super().__init__(
            "Upgrade PostgreSQL charm",
            "Upgrading PostgreSQL charm.",
            client,
            jhelper,
            manifest,
            model,
            ["postgresql"],
            "postgresql-plan",
            POSTGRESQL_CONFIG_KEY,
            POSTGRESQL_UNIT_TIMEOUT,
        )


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
        plan: list[BaseStep] = [
            UpgradePostgreSQLCharm(
                self.client,
                self.jhelper,
                self.manifest,
                self.deployment.infrastructure_model,
            )
        ]
        if self.client.cluster.list_nodes_by_role("haproxy"):
            plan.append(
                UpgradeHAProxyCharm(
                    self.client,
                    self.jhelper,
                    self.manifest,
                    self.deployment.infrastructure_model,
                )
            )
        if self.client.cluster.list_nodes_by_role("agent"):
            plan.append(
                UpgradeMAASAgentCharm(
                    self.client,
                    self.jhelper,
                    self.manifest,
                    self.deployment.infrastructure_model,
                )
            )
        if self.client.cluster.list_nodes_by_role("region"):
            plan.append(
                UpgradeMAASRegionCharm(
                    self.client,
                    self.jhelper,
                    self.manifest,
                    self.deployment.infrastructure_model,
                )
            )
        plan.append(UpgradePlugins(self.deployment, upgrade_release=True))
        return plan
