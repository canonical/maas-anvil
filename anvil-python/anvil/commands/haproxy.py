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
import os.path
from os import environ, mkdir
import logging
from typing import List

from rich.console import Console
from sunbeam.clusterd.client import Client
from sunbeam.commands.terraform import TerraformInitStep
from sunbeam.jobs import questions
from sunbeam.jobs.juju import JujuHelper
from sunbeam.jobs.manifest import BaseStep
from sunbeam.jobs.steps import (
    AddMachineUnitsStep,
    DeployMachineApplicationStep,
    RemoveMachineUnitStep,
)

from anvil.jobs.manifest import Manifest
from anvil.provider.local.deployment import LocalDeployment

APPLICATION = "haproxy"
CONFIG_KEY = "TerraformVarsHaproxyPlan"
ADDONS_CONFIG_KEY = "TerraformVarsHaproxyAddons"
HAPROXY_APP_TIMEOUT = 180  # 3 minutes, managing the application should be fast
HAPROXY_UNIT_TIMEOUT = (
    1200  # 15 minutes, adding / removing units can take a long time
)
HAPROXY_CERTS_DIR = os.path.join(environ['HOME'], "certs/")
LOG = logging.getLogger(__name__)


def validate_cert_file(filepath: str) -> None:
    if not os.path.isfile(filepath):
        raise ValueError(f"{filepath} does not exist")
    try:
        with open(filepath, "r") as f:
            parse_cert(f.read())
    except:
        raise ValueError("Invalid certificate file format")

def validate_key_file(filepath: str) -> None:
    if not os.path.isfile(filepath):
        raise ValueError(f"{filepath} does not exist")
    try:
        with open(filepath, "r") as f:
            parse_key(f.read())
    except:
        raise ValueError("Invalid key file format")

def parse_cert(cert: str) -> str:
    return '\n'.join([x for x in cert.split("\n") if x and "CERTIFICATE" not in x])

def parse_key(key: str) -> str:
    return '\n'.join([x for x in key.split("\n") if x and "KEY" not in x])


class DeployHAProxyApplicationStep(DeployMachineApplicationStep):
    """Deploy HAProxy application using Terraform"""

    _HAPROXY_ADDONS_QUESTIONS = {
        "ssl_cert": questions.PromptQuestion(
            "Path to SSL Certificate for HAProxy: ",
            validation_function=validate_cert_file,
        ),
        "ssl_key": questions.PromptQuestion(
            "Path to private key for the SSL certificate",
            validation_function=validate_key_file,
        ),
    }
    _TLS_SERVICES_CONFIG = f"""- service_name: haproxy_service
  service_host: "0.0.0.0"
  service_port: 443
  service_options:
    - balance leastconn
    - cookie SRVNAME insert
  server_options: maxconn 100 cookie S{"{i}"} check
  crts: [{HAPROXY_CERTS_DIR}]
"""

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
            "haproxy-plan",
            "Deploy HAProxy",
            "Deploying HAProxy",
            refresh,
        )
        self.variables = {"charm_haproxy_config": {}}

    def get_application_timeout(self) -> int:
        return HAPROXY_APP_TIMEOUT

    def has_prompts(self) -> bool:
        # maybe return False if it's a refresh?
        return True

    def prompt(self, console: Console | None = None) -> None:
        haproxy_addons_bank = questions.QuestionBank(
            questions=self._HAPROXY_ADDONS_QUESTIONS,
            console=console,
        )
        with open(haproxy_addons_bank.ssl_cert.ask(), "r") as cert_file:
            cert = cert_file.read()
        with open(haproxy_addons_bank.ssl_key.ask(), "r") as key_file:
            key = key_file.read()
        if not os.path.isdir(HAPROXY_CERTS_DIR):
            mkdir(HAPROXY_CERTS_DIR)
        with open(os.path.join(HAPROXY_CERTS_DIR, "haproxy.pem"), "w") as combined_file:
            combined_file.write(key + cert)
        
        self.variables["charm_haproxy_config"]["services"] = self._TLS_SERVICES_CONFIG
        LOG.debug(f"HAProxy prompt variables: {self.variables}")

        # TODO: do we need this? probably for refresh?
        questions.write_answers(self.client, ADDONS_CONFIG_KEY, self.variables)

        tfhelper = self.manifest.get_tfhelper(self.tfplan)
        answer_file = tfhelper.path / "addons.auto.tfvars.json"
        tfhelper.write_tfvars(self.variables, answer_file)

    def extra_tfvars(self) -> dict:
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
) -> List[BaseStep]:
    return [
        TerraformInitStep(manifest.get_tfhelper("haproxy-plan")),
        DeployHAProxyApplicationStep(
            client, manifest, jhelper, deployment.infrastructure_model
        ),
        AddHAProxyUnitsStep(
            client, fqdn, jhelper, deployment.infrastructure_model
        ),
    ]
