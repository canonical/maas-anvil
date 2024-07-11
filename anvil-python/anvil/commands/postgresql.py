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

from rich.status import Status
from sunbeam.clusterd.client import Client
from sunbeam.commands.terraform import TerraformInitStep
from sunbeam.jobs import questions
from sunbeam.jobs.common import BaseStep, Result, ResultType
from sunbeam.jobs.juju import JujuHelper
from sunbeam.jobs.steps import (
    AddMachineUnitsStep,
    DeployMachineApplicationStep,
    RemoveMachineUnitStep,
)

from anvil.jobs.manifest import Manifest

LOG = logging.getLogger(__name__)
APPLICATION = "postgresql"
CONFIG_KEY = "TerraformVarsPostgresqlPlan"
POSTGRESQL_CONFIG_KEY = "TerraformVarsPostgresql"
POSTGRESQL_APP_TIMEOUT = (
    180  # 3 minutes, managing the application should be fast
)
POSTGRESQL_UNIT_TIMEOUT = (
    1200  # 15 minutes, adding / removing units can take a long time
)


def postgresql_install_steps(
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
        TerraformInitStep(manifest.get_tfhelper("postgresql-plan")),
        DeployPostgreSQLApplicationStep(
            client,
            manifest,
            jhelper,
            model,
            accept_defaults=accept_defaults,
            deployment_preseed=preseed,
            refresh=refresh,
        ),
        AddPostgreSQLUnitsStep(client, fqdn, jhelper, model),
    ]


def postgresql_upgrade_steps(
    client: Client,
    manifest: Manifest,
    jhelper: JujuHelper,
    model: str,
    accept_defaults: bool,
    preseed: dict[Any, Any],
) -> List[BaseStep]:
    return [
        TerraformInitStep(manifest.get_tfhelper("postgresql-plan")),
        DeployPostgreSQLApplicationStep(
            client,
            manifest,
            jhelper,
            model,
            accept_defaults=accept_defaults,
            deployment_preseed=preseed,
            refresh=True,
        ),
    ]


def postgresql_questions() -> dict[str, questions.PromptQuestion]:
    return {
        "max_connections": questions.PromptQuestion(
            "Maximum number of concurrent connections to allow to the database server",
            default_value="default",
            validation_function=validate_max_connections,
        ),
    }


def validate_max_connections(value: str) -> str | ValueError:
    if value in ["default", "dynamic"]:
        return value
    try:
        if 100 <= int(value) <= 500:
            return value
        else:
            raise ValueError
    except ValueError:
        raise ValueError(
            "Please provide either a number between 100 and 500 or 'default' for system default or 'dynamic' for calculating max_connections relevant to maas regions"
        )


class DeployPostgreSQLApplicationStep(DeployMachineApplicationStep):
    """Deploy PostgreSQL application using Terraform"""

    _CONFIG = POSTGRESQL_CONFIG_KEY

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
            "postgresql-plan",
            "Deploy PostgreSQL",
            "Deploying PostgreSQL",
            refresh,
        )

        self.preseed = deployment_preseed or {}
        self.accept_defaults = accept_defaults

    def get_application_timeout(self) -> int:
        return POSTGRESQL_APP_TIMEOUT

    def prompt(self, console: questions.Console | None = None) -> None:
        variables = questions.load_answers(self.client, self._CONFIG)
        variables.setdefault("max_connections", "default")

        # Set defaults
        self.preseed.setdefault("max_connections", "default")

        postgresql_config_bank = questions.QuestionBank(
            questions=postgresql_questions(),
            console=console,
            preseed=self.preseed.get("postgres"),
            previous_answers=variables,
            accept_defaults=self.accept_defaults,
        )
        max_connections = postgresql_config_bank.max_connections.ask()
        variables["max_connections"] = max_connections

        LOG.debug(variables)
        questions.write_answers(self.client, self._CONFIG, variables)

    def extra_tfvars(self) -> dict[str, Any]:
        variables: dict[str, Any] = questions.load_answers(
            self.client, self._CONFIG
        )
        variables["maas_region_nodes"] = len(
            self.client.cluster.list_nodes_by_role("region")
        )
        return variables

    def has_prompts(self) -> bool:
        return True


class ReapplyPostgreSQLTerraformPlanStep(DeployMachineApplicationStep):
    """Reapply PostgreSQL Terraform plan"""

    _CONFIG = POSTGRESQL_CONFIG_KEY

    def __init__(
        self,
        client: Client,
        manifest: Manifest,
        jhelper: JujuHelper,
        model: str,
    ):
        super().__init__(
            client,
            manifest,
            jhelper,
            CONFIG_KEY,
            APPLICATION,
            model,
            "postgresql-plan",
            "Reapply PostgreSQL Terraform plan",
            "Reapplying PostgreSQL Terraform plan",
            True,
        )

    def get_application_timeout(self) -> int:
        return POSTGRESQL_APP_TIMEOUT

    def extra_tfvars(self) -> dict[str, Any]:
        variables: dict[str, Any] = questions.load_answers(
            self.client, self._CONFIG
        )
        variables["maas_region_nodes"] = len(
            self.client.cluster.list_nodes_by_role("region")
        )
        return variables

    def is_skip(self, status: Status | None = None) -> Result:
        variables: dict[str, Any] = questions.load_answers(
            self.client, self._CONFIG
        )
        variables.setdefault("max_connections", "default")
        if variables["max_connections"] != "dynamic":
            return Result(ResultType.SKIPPED)
        else:
            return super().is_skip(status)


class AddPostgreSQLUnitsStep(AddMachineUnitsStep):
    """Add PostgreSQL Unit."""

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
            "Add PostgreSQL unit",
            "Adding PostgreSQL unit to machine",
        )

    def get_unit_timeout(self) -> int:
        return POSTGRESQL_UNIT_TIMEOUT


class RemovePostgreSQLUnitStep(RemoveMachineUnitStep):
    """Remove PostgreSQL Unit."""

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
            "Remove PostgreSQL unit",
            "Removing PostgreSQL unit from machine",
        )

    def get_unit_timeout(self) -> int:
        return POSTGRESQL_UNIT_TIMEOUT
