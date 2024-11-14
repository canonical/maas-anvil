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

from sunbeam.clusterd.client import Client
from sunbeam.commands.terraform import TerraformException, TerraformInitStep
from sunbeam.jobs import questions
from sunbeam.jobs.common import BaseStep, ResultType
from sunbeam.jobs.juju import JujuHelper
from sunbeam.jobs.steps import (
    AddMachineUnitsStep,
    DeployMachineApplicationStep,
)

from anvil.commands.haproxy import HAPROXY_CONFIG_KEY, tls_questions
from anvil.jobs.manifest import Manifest
from anvil.jobs.steps import RemoveMachineUnitStep

LOG = logging.getLogger(__name__)

APPLICATION = "maas-region"
CONFIG_KEY = "TerraformVarsMaasregionPlan"
MAASREGION_CONFIG_KEY = "TerraformVarsMaasregion"
MAASREGION_APP_TIMEOUT = (
    180  # 3 minutes, managing the application should be fast
)
MAASREGION_UNIT_TIMEOUT = (
    1200  # 15 minutes, adding / removing units can take a long time
)
# If tls_mode is being asked here, haproxy is not enabled.
# So, TLS termination is not a valid config
MAAS_REGION_VALID_TLS_MODES = ["passthrough", "disabled"]


class DeployMAASRegionApplicationStep(DeployMachineApplicationStep):
    """Deploy MAAS Region application using Terraform"""

    _MAASREGION_CONFIG = MAASREGION_CONFIG_KEY

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
            "maas-region-plan",
            "Deploy MAAS Region",
            "Deploying MAAS Region",
            refresh,
        )
        self.preseed = deployment_preseed or {}
        self.accept_defaults = accept_defaults

    def get_application_timeout(self) -> int:
        return MAASREGION_APP_TIMEOUT

    def has_prompts(self) -> bool:
        if self.refresh:
            return False
        skip_result = self.is_skip()
        if skip_result.result_type == ResultType.SKIPPED:
            return False
        elif self.client.cluster.list_nodes_by_role("haproxy"):
            return False
        return True

    def prompt(self, console: questions.Console | None = None) -> None:
        variables = questions.load_answers(
            self.client, self._MAASREGION_CONFIG
        )
        variables.setdefault("ssl_cert", "")
        variables.setdefault("ssl_key", "")
        variables.setdefault("ssl_cacert", "")
        variables.setdefault("tls_mode", "disabled")

        self.preseed.setdefault("ssl_cert", "")
        self.preseed.setdefault("ssl_key", "")
        self.preseed.setdefault("ssl_cacert", "")
        self.preseed.setdefault("tls_mode", "disabled")

        maas_region_config_bank = questions.QuestionBank(
            questions=tls_questions(MAAS_REGION_VALID_TLS_MODES),
            console=console,
            preseed=self.preseed.get("maas-region"),
            previous_answers=variables,
            accept_defaults=self.accept_defaults,
        )
        tls_mode = maas_region_config_bank.tls_mode.ask()
        variables["tls_mode"] = tls_mode
        if tls_mode == "passthrough":
            variables["ssl_cert"] = maas_region_config_bank.ssl_cert.ask()
            variables["ssl_key"] = maas_region_config_bank.ssl_key.ask()
            variables["ssl_cacert"] = maas_region_config_bank.ssl_cacert.ask()

        LOG.debug(variables)
        questions.write_answers(
            self.client, self._MAASREGION_CONFIG, variables
        )

    def extra_tfvars(self) -> dict[str, Any]:
        enable_haproxy = (
            True
            if self.client.cluster.list_nodes_by_role("haproxy")
            else False
        )
        variables: dict[str, Any] = {"enable_haproxy": enable_haproxy}
        answers: dict[str, Any] = {}
        if enable_haproxy:
            answers = questions.load_answers(self.client, HAPROXY_CONFIG_KEY)
        else:
            answers = questions.load_answers(
                self.client, self._MAASREGION_CONFIG
            )
        variables["tls_mode"] = answers["tls_mode"]
        if variables["tls_mode"] == "passthrough":
            if not answers["ssl_cert"] or not answers["ssl_key"]:
                raise TerraformException(
                    "Both ssl_cert and ssl_key must be provided when enabling TLS"
                )
            with open(answers["ssl_cert"]) as cert_file:
                variables["ssl_cert_content"] = cert_file.read()
            with open(answers["ssl_key"]) as key_file:
                variables["ssl_key_content"] = key_file.read()
            if answers["ssl_cacert"]:
                with open(answers["ssl_cacert"]) as cacert_file:
                    variables["ssl_cacert_content"] = cacert_file.read()
        return variables


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


def maas_region_install_steps(
    client: Client,
    manifest: Manifest,
    jhelper: JujuHelper,
    model: str,
    fqdn: str,
    accept_defaults: bool,
    preseed: dict[Any, Any],
) -> List[BaseStep]:
    return [
        TerraformInitStep(manifest.get_tfhelper("maas-region-plan")),
        DeployMAASRegionApplicationStep(
            client,
            manifest,
            jhelper,
            model,
            deployment_preseed=preseed,
            accept_defaults=accept_defaults,
        ),
        AddMAASRegionUnitsStep(client, fqdn, jhelper, model),
    ]


def maas_region_upgrade_steps(
    client: Client,
    manifest: Manifest,
    jhelper: JujuHelper,
    model: str,
    preseed: dict[Any, Any],
) -> List[BaseStep]:
    return [
        TerraformInitStep(manifest.get_tfhelper("maas-region-plan")),
        DeployMAASRegionApplicationStep(
            client,
            manifest,
            jhelper,
            model,
            deployment_preseed=preseed,
            refresh=True,
        ),
    ]
