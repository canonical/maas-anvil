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
from sunbeam.clusterd.client import Client
from sunbeam.jobs.common import (
    BaseStep,
)
from sunbeam.jobs.deployment import Deployment
from sunbeam.jobs.juju import JujuHelper

from anvil.commands.haproxy import (
    UpgradeHAProxyUnitCharms,
)
from anvil.commands.maas_agent import (
    UpgradeMAASAgentUnitCharms,
)
from anvil.commands.maas_region import (
    UpgradeMAASRegionUnitCharms,
)
from anvil.commands.postgresql import (
    UpgradePostgreSQLUnitCharms,
)
from anvil.commands.upgrades.base import (
    UpgradePlugins,
)
from anvil.jobs.manifest import Manifest

LOG = logging.getLogger(__name__)
console = Console()


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
            UpgradePlugins(self.deployment, upgrade_release=True),
        ]
        return plan
