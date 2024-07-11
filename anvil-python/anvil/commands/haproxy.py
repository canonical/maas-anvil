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

import ipaddress
import logging
from typing import Any, List

from rich.console import Console
from sunbeam.clusterd.client import Client
from sunbeam.commands.terraform import TerraformInitStep
from sunbeam.jobs import questions
from sunbeam.jobs.common import BaseStep
from sunbeam.jobs.juju import JujuHelper
from sunbeam.jobs.steps import (
    AddMachineUnitsStep,
    DeployMachineApplicationStep,
    RemoveMachineUnitStep,
)

from anvil.jobs.manifest import Manifest

LOG = logging.getLogger(__name__)

APPLICATION = "haproxy"
CONFIG_KEY = "TerraformVarsHaproxyPlan"
HAPROXY_CONFIG_KEY = "TerraformVarsHaproxy"
KEEPALIVED_CONFIG_KEY = "TerraformVarsKeepalived"
HAPROXY_APP_TIMEOUT = 180  # 3 minutes, managing the application should be fast
HAPROXY_UNIT_TIMEOUT = (
    1200  # 15 minutes, adding / removing units can take a long time
)


def keepalived_questions() -> dict[str, questions.PromptQuestion]:
    return {
        "virtual_ip": questions.PromptQuestion(
            "Virtual IP to use for the Cluster in HA",
            default_value="",
            validation_function=validate_virtual_ip,
        ),
    }


def validate_virtual_ip(value: str) -> str:
    """We allow passing an empty IP for virtual_ip"""
    if value == "":
        return ""
    try:
        return ipaddress.ip_address(value).exploded
    except ValueError as e:
        raise ValueError(f"{value} is not a valid IP address: {e}")


class DeployHAProxyApplicationStep(DeployMachineApplicationStep):
    """Deploy HAProxy application using Terraform"""

    _KEEPALIVED_CONFIG = KEEPALIVED_CONFIG_KEY

    def __init__(
        self,
        client: Client,
        manifest: Manifest,
        jhelper: JujuHelper,
        model: str,
        deployment_preseed: dict[Any, Any] | None = None,
        accept_defaults: bool = False,
        refresh: bool = False,
    ):
        super().__init__(
            client,
            manifest,
            jhelper,
            CONFIG_KEY,
            APPLICATION,
            model,
            "haproxy-plan",
            "Deploy HAProxy",
            "Deploying HAProxy",
            refresh,
        )
        self.preseed = deployment_preseed or {}
        self.accept_defaults = accept_defaults

    def get_application_timeout(self) -> int:
        return HAPROXY_APP_TIMEOUT

    def has_prompts(self) -> bool:
        return True

    def prompt(self, console: Console | None = None) -> None:
        variables = questions.load_answers(
            self.client, self._KEEPALIVED_CONFIG
        )
        variables.setdefault("virtual_ip", "")

        # Set defaults
        self.preseed.setdefault("virtual_ip", "")

        keepalived_config_bank = questions.QuestionBank(
            questions=keepalived_questions(),
            console=console,
            preseed=self.preseed.get("haproxy"),
            previous_answers=variables,
            accept_defaults=self.accept_defaults,
        )

        variables["virtual_ip"] = keepalived_config_bank.virtual_ip.ask()

        LOG.debug(variables)
        questions.write_answers(
            self.client, self._KEEPALIVED_CONFIG, variables
        )

    def extra_tfvars(self) -> dict[str, Any]:
        variables: dict[str, Any] = questions.load_answers(
            self.client, self._KEEPALIVED_CONFIG
        )
        variables["haproxy_port"] = 80
        return variables


class AddHAProxyUnitsStep(AddMachineUnitsStep):
    """Add HAProxy Unit."""

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
            "Add HAProxy unit",
            "Adding HAProxy unit to machine",
        )

    def get_unit_timeout(self) -> int:
        return HAPROXY_UNIT_TIMEOUT


class RemoveHAProxyUnitStep(RemoveMachineUnitStep):
    """Remove HAProxy Unit."""

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
            "Remove HAProxy unit",
            "Removing HAProxy unit from machine",
        )

    def get_unit_timeout(self) -> int:
        return HAPROXY_UNIT_TIMEOUT


def haproxy_install_steps(
    client: Client,
    manifest: Manifest,
    jhelper: JujuHelper,
    model: str,
    fqdn: str,
    accept_defaults: bool,
    preseed: dict[Any, Any],
    refresh: bool = False,
) -> List[BaseStep]:
    return [
        TerraformInitStep(manifest.get_tfhelper("haproxy-plan")),
        DeployHAProxyApplicationStep(
            client,
            manifest,
            jhelper,
            model,
            accept_defaults=accept_defaults,
            deployment_preseed=preseed,
            refresh=refresh,
        ),
        AddHAProxyUnitsStep(client, fqdn, jhelper, model),
    ]


def haproxy_upgrade_steps(
    client: Client,
    manifest: Manifest,
    jhelper: JujuHelper,
    model: str,
    accept_defaults: bool,
    preseed: dict[Any, Any],
) -> List[BaseStep]:
    return [
        TerraformInitStep(manifest.get_tfhelper("haproxy-plan")),
        DeployHAProxyApplicationStep(
            client,
            manifest,
            jhelper,
            model,
            accept_defaults=accept_defaults,
            deployment_preseed=preseed,
            refresh=True,
        ),
    ]
