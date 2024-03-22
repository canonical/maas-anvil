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

from sunbeam.clusterd.client import Client
from sunbeam.jobs.juju import JujuHelper
from sunbeam.jobs.steps import (
    AddMachineUnitsStep,
    DeployMachineApplicationStep,
    RemoveMachineUnitStep,
)

from anvil.jobs.manifest import Manifest

APPLICATION = "postgresql"
CONFIG_KEY = "TerraformVarsPostgresqlPlan"
POSTGRESQL_APP_TIMEOUT = (
    180  # 3 minutes, managing the application should be fast
)
POSTGRESQL_UNIT_TIMEOUT = (
    1200  # 15 minutes, adding / removing units can take a long time
)


class DeployPostgreSQLApplicationStep(DeployMachineApplicationStep):
    """Deploy PostgreSQL application using Terraform"""

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
            "postgresql-plan",
            "Deploy PostgreSQL",
            "Deploying PostgreSQL",
            refresh,
        )

    def get_application_timeout(self) -> int:
        return POSTGRESQL_APP_TIMEOUT


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
