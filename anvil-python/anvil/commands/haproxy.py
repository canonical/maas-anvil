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
from typing import Any, List

from rich.console import Console
from sunbeam.clusterd.client import Client
from sunbeam.commands.terraform import TerraformInitStep
from sunbeam.jobs.juju import JujuHelper
from sunbeam.jobs.manifest import BaseStep
from sunbeam.jobs.questions import (
    PromptQuestion,
    QuestionBank,
    load_answers,
    write_answers,
)
from sunbeam.jobs.steps import (
    AddMachineUnitsStep,
    DeployMachineApplicationStep,
    RemoveMachineUnitStep,
)

from anvil.jobs.common import (
    validate_ip_address,
)
from anvil.jobs.manifest import Manifest

LOG = logging.getLogger(__name__)
from anvil.provider.local.deployment import LocalDeployment

APPLICATION = "haproxy"
CONFIG_KEY = "TerraformVarsHaproxyPlan"
HAPROXY_CONFIG_KEY = "TerraformVarsHaproxy"
KEEPALIVED_CONFIG_KEY = "TerraformVarsKeepalived"
HAPROXY_APP_TIMEOUT = 180  # 3 minutes, managing the application should be fast
HAPROXY_UNIT_TIMEOUT = (
    1200  # 15 minutes, adding / removing units can take a long time
)

CONF_VAR = dict[str, dict[str, Any]]


def keepalived_questions() -> dict[str, Any]:
    return {"virtual_ip": "", "vip_hostname": "", "port": 443}


class DeployHAProxyApplicationStep(DeployMachineApplicationStep):
    """Deploy HAProxy application using Terraform"""

    def __init__(
        self,
        client: Client,
        manifest: Manifest,
        jhelper: JujuHelper,
        model: str,
        refresh: bool = False,
        accept_defaults: bool = False,
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
        self.variables: CONF_VAR = {}
        self.accept_defaults = accept_defaults

    def get_application_timeout(self) -> int:
        return HAPROXY_APP_TIMEOUT

    def has_prompts(self) -> bool:
        return True

    def prompt(self, console: Console | None = None) -> None:
        self.variables = load_answers(self.client, KEEPALIVED_CONFIG_KEY)
        self.variables.setdefault("keepalived_config", {})
        self.variables["keepalived_config"].setdefault("virtual_ip", "")
        self.variables["keepalived_config"].setdefault("vip_hostname", "")
        self.variables["keepalived_config"].setdefault("port", 443)

        keepalive_bank = QuestionBank(
            questions={
                "virtual_ip": PromptQuestion(
                    "Virtual IP to use for the Cluster in HA",
                    default_value=keepalived_questions().get("virtual_ip"),
                    validation_function=validate_ip_address,
                ),
                "vip_hostname": PromptQuestion(
                    "Virtual IP hostname for the Cluster in HA",
                    default_value=keepalived_questions().get("vip_hostname"),
                ),
                "port": PromptQuestion(
                    "Virtual IP port to use for the Cluster in HA",
                    default_value=keepalived_questions().get("port"),
                ),
            },
            console=console,
            previous_answers=self.variables,
            accept_defaults=self.accept_defaults,
        )

        self.variables["keepalived_config"]["virtual_ip"] = (
            keepalive_bank.virtual_ip.ask()
        )
        self.variables["keepalived_config"]["vip_hostname"] = (
            keepalive_bank.vip_hostname.ask()
        )
        self.variables["keepalived_config"]["port"] = keepalive_bank.port.ask()

        LOG.debug(self.variables)
        write_answers(self.client, CONFIG_KEY, self.variables)

    def extra_tfvars(self) -> dict[str, Any]:
        return self.variables


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
    deployment: LocalDeployment,
    fqdn: str,
    accept_defaults: bool = False,
) -> List[BaseStep]:
    return [
        TerraformInitStep(manifest.get_tfhelper("haproxy-plan")),
        DeployHAProxyApplicationStep(
            client,
            manifest,
            jhelper,
            deployment.infrastructure_model,
            accept_defaults=accept_defaults,
        ),
        AddHAProxyUnitsStep(
            client, fqdn, jhelper, deployment.infrastructure_model
        ),
    ]
