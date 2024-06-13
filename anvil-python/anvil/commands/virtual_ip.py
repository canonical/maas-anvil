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

from typing import Any

from sunbeam.clusterd.client import Client
from sunbeam.jobs.juju import JujuHelper
from sunbeam.jobs.steps import (
    AddMachineUnitsStep,
    DeployMachineApplicationStep,
    RemoveMachineUnitStep,
)

from anvil.jobs.manifest import Manifest

APPLICATION = "virtual_ip"
CONFIG_KEY = "TerraformVarsVirtualIPPlan"
VIRTUALIP_APP_TIMEOUT = (
    180  # 3 minutes, managing the application should be fast
)
VIRTUALIP_UNIT_TIMEOUT = (
    1200  # 15 minutes, adding / removing units can take a long time
)


class DeployVirtualIpApplicationStep(DeployMachineApplicationStep):
    """Deploy VirtualIp application using Terraform"""

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
            "virtual-ip-plan",
            "Deploy VirtualIp",
            "Deploying VirtualIp",
            refresh,
        )

    def get_application_timeout(self) -> int:
        return VIRTUALIP_APP_TIMEOUT

    def extra_tfvars(self) -> dict[str, Any]:
        # TODO: How do we pass the VIP from command line to here?
        if virtual_ip := None:
            return {"virtual_ip": virtual_ip}
        return {}


class AddVirtualIpUnitsStep(AddMachineUnitsStep):
    """Add VirtualIp Unit."""

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
            "Add VirtualIp unit",
            "Adding VirtualIp unit to machine",
        )

    def get_unit_timeout(self) -> int:
        return VIRTUALIP_UNIT_TIMEOUT


class RemoveVirtualIpUnitStep(RemoveMachineUnitStep):
    """Remove VirtualIp Unit."""

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
            "Remove VirtualIp unit",
            "Removing VirtualIp unit from machine",
        )

    def get_unit_timeout(self) -> int:
        return VIRTUALIP_UNIT_TIMEOUT
