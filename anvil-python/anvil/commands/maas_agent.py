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

from typing import List

from sunbeam.clusterd.client import Client
from sunbeam.commands.terraform import TerraformInitStep
from sunbeam.jobs.common import BaseStep
from sunbeam.jobs.juju import JujuHelper
from sunbeam.jobs.steps import (
    AddMachineUnitsStep,
    DeployMachineApplicationStep,
)

from anvil.jobs.manifest import Manifest
from anvil.jobs.steps import RemoveMachineUnitStep
from anvil.utils import UpgradeCharm

APPLICATION = "maas-agent"
CONFIG_KEY = "TerraformVarsMaasagentPlan"
MAASAGENT_APP_TIMEOUT = (
    180  # 3 minutes, managing the application should be fast
)
MAASAGENT_UNIT_TIMEOUT = (
    1200  # 15 minutes, adding / removing units can take a long time
)


class DeployMAASAgentApplicationStep(DeployMachineApplicationStep):
    """Deploy MAAS Agent application using Terraform"""

    def __init__(
        self,
        client: Client,
        manifest: Manifest,
        jhelper: JujuHelper,
        model: str,
        refresh: bool = False,
    ):
        super().__init__(
            client,
            manifest,
            jhelper,
            CONFIG_KEY,
            APPLICATION,
            model,
            "maas-agent-plan",
            "Deploy MAAS Agent",
            "Deploying MAAS Agent",
            refresh,
        )

    def get_application_timeout(self) -> int:
        return MAASAGENT_APP_TIMEOUT


class AddMAASAgentUnitsStep(AddMachineUnitsStep):
    """Add MAAS Agent Unit."""

    def __init__(
        self,
        client: Client,
        names: list[str] | str,
        jhelper: JujuHelper,
        model: str,
    ):
        super().__init__(
            client,
            names,
            jhelper,
            CONFIG_KEY,
            APPLICATION,
            model,
            "Add MAAS Agent unit",
            "Adding MAAS Agent unit to machine",
        )

    def get_unit_timeout(self) -> int:
        return MAASAGENT_UNIT_TIMEOUT


class RemoveMAASAgentUnitStep(RemoveMachineUnitStep):
    """Remove MAAS Agent Unit."""

    def __init__(
        self, client: Client, name: str, jhelper: JujuHelper, model: str
    ):
        super().__init__(
            client,
            name,
            jhelper,
            CONFIG_KEY,
            APPLICATION,
            model,
            "Remove MAAS Agent unit",
            "Removing MAAS Agent unit from machine",
        )

    def get_unit_timeout(self) -> int:
        return MAASAGENT_UNIT_TIMEOUT


class UpgradeMAASAgentUnitCharms(UpgradeCharm):
    def __init__(
        self,
        client: Client,
        jhelper: JujuHelper,
        manifest: Manifest,
        model: str,
    ):
        super().__init__(
            "Upgrade MAAS Agent unit charms",
            "Upgrading MAAS Agent unit charms.",
            client,
            jhelper,
            manifest,
            model,
            ["maas-agent"],
            "maas-agent-plan",
            CONFIG_KEY,
            MAASAGENT_UNIT_TIMEOUT,
        )


def maas_agent_install_steps(
    client: Client,
    manifest: Manifest,
    jhelper: JujuHelper,
    model: str,
    fqdn: str,
    refresh: bool = False,
) -> List[BaseStep]:
    return [
        TerraformInitStep(manifest.get_tfhelper("maas-agent-plan")),
        DeployMAASAgentApplicationStep(
            client, manifest, jhelper, model, refresh=refresh
        ),
        AddMAASAgentUnitsStep(client, fqdn, jhelper, model),
    ]


def maas_agent_upgrade_steps(
    client: Client,
    manifest: Manifest,
    jhelper: JujuHelper,
    model: str,
) -> List[BaseStep]:
    return [
        TerraformInitStep(manifest.get_tfhelper("maas-agent-plan")),
        DeployMAASAgentApplicationStep(
            client, manifest, jhelper, model, refresh=True
        ),
    ]
