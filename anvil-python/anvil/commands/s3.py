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
from sunbeam.commands.terraform import TerraformInitStep
from sunbeam.jobs import questions
from sunbeam.jobs.common import BaseStep
from sunbeam.jobs.juju import JujuHelper
from sunbeam.jobs.steps import (
    AddMachineUnitsStep,
    DeployMachineApplicationStep,
)

from anvil.jobs.manifest import Manifest
from anvil.jobs.steps import RemoveMachineUnitStep
from anvil.utils import get_architecture

LOG = logging.getLogger(__name__)
APPLICATION = "s3-integrator"
CONFIG_KEY = "TerraformVarsS3Plan"
S3_CONFIG_KEY = "TerraformVarsS3"
S3_APP_TIMEOUT = 180  # 3 minutes, managing the application should be fast
S3_UNIT_TIMEOUT = (
    1200  # 15 minutes, adding / removing units can take a long time
)


def s3_install_steps(
    client: Client,
    manifest: Manifest,
    jhelper: JujuHelper,
    model: str,
    fqdn: str,
    accept_defaults: bool,
    preseed: dict[Any, Any],
) -> List[BaseStep]:
    return [
        TerraformInitStep(manifest.get_tfhelper("s3-plan")),
        DeployS3ApplicationStep(
            client,
            manifest,
            jhelper,
            model,
            accept_defaults=accept_defaults,
            deployment_preseed=preseed,
        ),
        AddS3UnitsStep(client, fqdn, jhelper, model),
    ]


def s3_upgrade_steps(
    client: Client,
    manifest: Manifest,
    jhelper: JujuHelper,
    model: str,
    preseed: dict[Any, Any],
) -> List[BaseStep]:
    return [
        TerraformInitStep(manifest.get_tfhelper("s3-plan")),
        DeployS3ApplicationStep(
            client,
            manifest,
            jhelper,
            model,
            deployment_preseed=preseed,
            refresh=True,
            verb="Refresh",
        ),
    ]


def s3_questions() -> dict[str, questions.PromptQuestion]:
    return {}


class DeployS3ApplicationStep(DeployMachineApplicationStep):
    """Deploy S3 application using Terraform"""

    _CONFIG = S3_CONFIG_KEY

    def __init__(
        self,
        client: Client,
        manifest: Manifest,
        jhelper: JujuHelper,
        model: str,
        deployment_preseed: dict[Any, Any] | None = None,
        accept_defaults: bool = False,
        refresh: bool = False,
        verb: str = "Deploy",
    ):
        super().__init__(
            client,
            manifest,
            jhelper,
            CONFIG_KEY,
            APPLICATION,
            model,
            "s3-plan",
            f"{verb.capitalize()} S3",
            f"{verb.capitalize()}ing S3",
            refresh,
        )

        self.preseed = deployment_preseed or {}
        self.accept_defaults = accept_defaults

    def get_application_timeout(self) -> int:
        return S3_APP_TIMEOUT

    def extra_tfvars(self) -> dict[str, Any]:
        variables: dict[str, Any] = questions.load_answers(
            self.client, self._CONFIG
        )
        if get_architecture() == "arm64":
            variables["arch"] = "arm64"
        return variables


class AddS3UnitsStep(AddMachineUnitsStep):
    """Add S3 Unit."""

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
            "Add S3 unit",
            "Adding S3 unit to machine",
        )

    def get_unit_timeout(self) -> int:
        return S3_UNIT_TIMEOUT


class RemoveS3UnitStep(RemoveMachineUnitStep):
    """Remove S3 Unit."""

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
            "Remove S3 unit",
            "Removing S3 unit from machine",
        )

    def get_unit_timeout(self) -> int:
        return S3_UNIT_TIMEOUT
