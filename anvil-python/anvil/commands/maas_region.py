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

from typing import Any, List

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

APPLICATION = "maas-region"
CONFIG_KEY = "TerraformVarsMaasregionPlan"
MAASREGION_APP_TIMEOUT = (
    180  # 3 minutes, managing the application should be fast
)
MAASREGION_UNIT_TIMEOUT = (
    1200  # 15 minutes, adding / removing units can take a long time
)


class DeployMAASRegionApplicationStep(DeployMachineApplicationStep):
    """Deploy MAAS Region application using Terraform"""

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
            "maas-region-plan",
            "Deploy MAAS Region",
            "Deploying MAAS Region",
            refresh,
        )

    def get_application_timeout(self) -> int:
        return MAASREGION_APP_TIMEOUT

    def extra_tfvars(self) -> dict[str, Any]:
        enable_haproxy = (
            True
            if self.client.cluster.list_nodes_by_role("haproxy")
            else False
        )
        return {"enable_haproxy": enable_haproxy}


class AddMAASRegionUnitsStep(AddMachineUnitsStep):
    """Add MAAS Region Unit."""

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
            "Add MAAS Region unit",
            "Adding MAAS Region unit to machine",
        )

    def get_unit_timeout(self) -> int:
        return MAASREGION_UNIT_TIMEOUT


class RemoveMAASRegionUnitStep(RemoveMachineUnitStep):
    """Remove MAAS Region Unit."""

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
            "Remove MAAS Region unit",
            "Removing MAAS Region unit from machine",
        )

    def get_unit_timeout(self) -> int:
        return MAASREGION_UNIT_TIMEOUT


class UpgradeMAASRegionUnitCharms(UpgradeCharm):
    def __init__(
        self,
        client: Client,
        jhelper: JujuHelper,
        manifest: Manifest,
        model: str,
    ):
        super().__init__(
            "Upgrade MAAS Region unit charms",
            "Upgrading MAAS Region unit charms.",
            client,
            jhelper,
            manifest,
            model,
            ["maas-region", "pgbouncer"],
            "maas-region-plan",
            CONFIG_KEY,
            MAASREGION_UNIT_TIMEOUT,
        )


def maas_region_install_steps(
    client: Client,
    manifest: Manifest,
    jhelper: JujuHelper,
    model: str,
    fqdn: str,
    refresh: bool = False,
) -> List[BaseStep]:
    return [
        TerraformInitStep(manifest.get_tfhelper("maas-region-plan")),
        DeployMAASRegionApplicationStep(
            client, manifest, jhelper, model, refresh
        ),
        AddMAASRegionUnitsStep(client, fqdn, jhelper, model),
    ]


def maas_region_upgrade_steps(
    client: Client,
    manifest: Manifest,
    jhelper: JujuHelper,
    model: str,
) -> List[BaseStep]:
    return [
        TerraformInitStep(manifest.get_tfhelper("maas-region-plan")),
        DeployMAASRegionApplicationStep(
            client, manifest, jhelper, model, refresh=True
        ),
    ]
