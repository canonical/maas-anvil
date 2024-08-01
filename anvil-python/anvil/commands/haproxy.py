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
import os.path
from typing import Any, List

from rich.console import Console
from sunbeam.clusterd.client import Client
from sunbeam.commands.terraform import TerraformInitStep
from sunbeam.jobs import questions
from sunbeam.jobs.common import BaseStep, ResultType
from sunbeam.jobs.juju import JujuHelper
from sunbeam.jobs.steps import (
    AddMachineUnitsStep,
    DeployMachineApplicationStep,
)
from sunbeam.utils import get_local_ip_by_default_route

from anvil.jobs.manifest import Manifest
from anvil.jobs.steps import RemoveMachineUnitStep

LOG = logging.getLogger(__name__)

APPLICATION = "haproxy"
CONFIG_KEY = "TerraformVarsHaproxyPlan"
HAPROXY_CONFIG_KEY = "TerraformVarsHaproxy"
HAPROXY_APP_TIMEOUT = 180  # 3 minutes, managing the application should be fast
HAPROXY_UNIT_TIMEOUT = (
    1200  # 15 minutes, adding / removing units can take a long time
)
LOG = logging.getLogger(__name__)


def validate_cert_file(filepath: str | None) -> None:
    if filepath is None:
        return
    if not os.path.isfile(filepath):
        raise ValueError(f"{filepath} does not exist")
    with open(filepath) as f:
        if "BEGIN CERTIFICATE" not in f.read():
            raise ValueError("Invalid certificate file")


def validate_key_file(filepath: str | None) -> None:
    if filepath is None:
        return
    if not os.path.isfile(filepath):
        raise ValueError(f"{filepath} does not exist")
    with open(filepath) as f:
        if "BEGIN PRIVATE KEY" not in f.read():
            raise ValueError("Invalid key file")


def validate_virtual_ip(value: str) -> str:
    """We allow passing an empty IP for virtual_ip"""
    if value == "":
        return ""
    try:
        return ipaddress.ip_address(value).exploded
    except ValueError as e:
        raise ValueError(f"{value} is not a valid IP address: {e}")


def haproxy_questions() -> dict[str, questions.PromptQuestion]:
    return {
        "virtual_ip": questions.PromptQuestion(
            "Virtual IP to use for the Cluster in HA",
            default_value="",
            validation_function=validate_virtual_ip,
        ),
        "ssl_cert": questions.PromptQuestion(
            "Path to SSL Certificate for HAProxy (enter nothing to skip TLS)",
            default_value=None,
            validation_function=validate_cert_file,
        ),
        "ssl_key": questions.PromptQuestion(
            "Path to private key for the SSL certificate (enter nothing to skip TLS)",
            default_value=None,
            validation_function=validate_key_file,
        ),
    }


class DeployHAProxyApplicationStep(DeployMachineApplicationStep):
    """Deploy HAProxy application using Terraform"""

    _HAPROXY_CONFIG = HAPROXY_CONFIG_KEY

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
        """Returns true if the step has prompts that it can ask the user.

        :return: True if the step can ask the user for prompts,
                 False otherwise
        """
        # No need to prompt for questions in case of refresh
        if self.refresh:
            return False
        skip_result = self.is_skip()
        if skip_result.result_type == ResultType.SKIPPED:
            return False
        else:
            return True

    def prompt(self, console: Console | None = None) -> None:
        variables = questions.load_answers(self.client, self._HAPROXY_CONFIG)
        variables.setdefault("virtual_ip", "")
        variables.setdefault("ssl_cert", None)
        variables.setdefault("ssl_key", None)

        # Set defaults
        self.preseed.setdefault("virtual_ip", "")
        self.preseed.setdefault("ssl_cert", None)
        self.preseed.setdefault("ssl_key", None)

        haproxy_config_bank = questions.QuestionBank(
            questions=haproxy_questions(),
            console=console,
            preseed=self.preseed.get("haproxy"),
            previous_answers=variables,
            accept_defaults=self.accept_defaults,
        )

        cert_filepath = haproxy_config_bank.ssl_cert.ask()
        variables["ssl_cert"] = cert_filepath
        key_filepath = haproxy_config_bank.ssl_key.ask()
        variables["ssl_key"] = key_filepath
        virtual_ip = haproxy_config_bank.virtual_ip.ask()
        variables["virtual_ip"] = virtual_ip

        if variables["virtual_ip"] == "" and variables["ssl_cert"] is not None:
            # VIP required for TLS configuration
            while variables["virtual_ip"] == "":
                if console:
                    console.print("Virtual IP is required when using TLS.")
                variables["virtual_ip"] = haproxy_config_bank.virtual_ip.ask()

        LOG.debug(variables)
        questions.write_answers(self.client, self._HAPROXY_CONFIG, variables)

    def extra_tfvars(self) -> dict[str, Any]:
        variables: dict[str, Any] = questions.load_answers(
            self.client, self._HAPROXY_CONFIG
        )

        cert_filepath = variables["ssl_cert"]
        key_filepath = variables["ssl_key"]
        if cert_filepath is not None and key_filepath is not None:
            with open(cert_filepath) as cert_file:
                variables["ssl_cert_content"] = cert_file.read()
            with open(key_filepath) as key_file:
                variables["ssl_key_content"] = key_file.read()
            variables["haproxy_port"] = 443
            variables["haproxy_services_yaml"] = self.get_tls_services_yaml(
                variables["virtual_ip"]
            )
        else:
            variables["haproxy_port"] = 80

        # Terraform does not need the content of these answers
        variables.pop("ssl_cert", None)
        variables.pop("ssl_key", None)

        LOG.debug(f"extra tfvars: {variables}")
        return variables

    def get_tls_services_yaml(self, vip: str) -> str:
        """Get the HAProxy services.yaml for TLS, inserting the VIP for the frontend bind"""
        services: str = (
            """- service_name: haproxy_service
  service_host: """
            ""
            + vip
            + """
  service_port: 443
  service_options:
    - balance leastconn
    - cookie SRVNAME insert
    - http-request redirect scheme https unless { ssl_fc }
  server_options: maxconn 100 cookie S{i} check
  crts: [DEFAULT]
- service_name: agent-service
  service_host: """
            + get_local_ip_by_default_route()
            + """
  service_port: 80
  service_options:
    - balance leastconn
    - cookie SRVNAME insert
    - acl is-internal src 10.30.0.0/24
    - use_backend haproxy_service if is-internal
  server_options: maxconn 100 cookie S{i} check
"""
        )
        return services


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
        ),
        AddHAProxyUnitsStep(client, fqdn, jhelper, model),
    ]


def haproxy_upgrade_steps(
    client: Client,
    manifest: Manifest,
    jhelper: JujuHelper,
    model: str,
    preseed: dict[Any, Any],
) -> List[BaseStep]:
    return [
        TerraformInitStep(manifest.get_tfhelper("haproxy-plan")),
        DeployHAProxyApplicationStep(
            client,
            manifest,
            jhelper,
            model,
            deployment_preseed=preseed,
            refresh=True,
        ),
    ]
