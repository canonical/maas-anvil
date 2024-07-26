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

from rich.console import Console
from rich.status import Status
from sunbeam.jobs.common import (
    BaseStep,
    Result,
    ResultType,
)
from sunbeam.jobs.deployment import Deployment

from anvil.jobs.plugin import PluginManager

LOG = logging.getLogger(__name__)
console = Console()


class UpgradePlugins(BaseStep):
    def __init__(
        self,
        deployment: Deployment,
        upgrade_release: bool = False,
    ):
        """Upgrade plugins.

        :client: Helper for interacting with clusterd
        :upgrade_release: Whether to upgrade channel
        """
        super().__init__("Validation", "Running pre-upgrade validation")
        self.deployment = deployment
        self.upgrade_release = upgrade_release

    def run(self, status: Status | None = None) -> Result:
        PluginManager.update_plugins(
            self.deployment,
            repos=["core"],
            upgrade_release=self.upgrade_release,
        )
        return Result(ResultType.COMPLETED)
