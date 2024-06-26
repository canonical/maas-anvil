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
import os

from sunbeam.jobs.checks import (
    DaemonGroupCheck as SunbeamDaemonGroupCheck,
    SystemRequirementsCheck as SunbeamSystemRequirementsCheck,
    VerifyBootstrappedCheck as SunbeamVerifyBootstrappedCheck,
)
from sunbeam.jobs.common import (
    get_host_total_cores,
    get_host_total_ram,
)

from anvil.jobs.common import RAM_4_GB_IN_KB

LOG = logging.getLogger(__name__)


class SystemRequirementsCheck(SunbeamSystemRequirementsCheck):
    """Check if machine has minimum 4 cores and 16GB RAM."""

    def run(self) -> bool:
        host_total_ram = get_host_total_ram()
        host_total_cores = get_host_total_cores()
        if host_total_ram < RAM_4_GB_IN_KB or host_total_cores < 2:
            self.message = "WARNING: Minimum system requirements (2 core CPU, 4 GB RAM) not met."
            LOG.warning(self.message)

        return True


class DaemonGroupCheck(SunbeamDaemonGroupCheck):
    """Check if user is member of socket group."""

    def run(self) -> bool:
        ret: bool = super().run()
        if not ret:
            self.message: str = self.message.replace("sunbeam", "anvil")
        return ret


class VerifyBootstrappedCheck(SunbeamVerifyBootstrappedCheck):
    """Check deployment has been bootstrapped."""

    def run(self) -> bool:
        ret: bool = super().run()
        if not ret:
            self.message: str = self.message.replace("sunbeam", "anvil")
        return ret
