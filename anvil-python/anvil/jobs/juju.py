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
import subprocess

from rich.status import Status
from sunbeam.commands.juju import ScaleJujuStep
from sunbeam.jobs.common import Result, ResultType

CONTROLLER = "anvil-controller"
LOG = logging.getLogger(__name__)


class AnvilScaleJujuStep(ScaleJujuStep):
    def run(self, status: Status | None = None) -> Result:
        cmd = [
            self._get_juju_binary(),
            "enable-ha",
            "-n",
            str(self.n),
            *self.extra_args,
        ]
        LOG.debug(f'Running command {" ".join(cmd)}')
        process = subprocess.run(
            cmd, capture_output=True, text=True, check=True
        )
        LOG.debug(
            f"Command finished. stdout={process.stdout}, stderr={process.stderr}"
        )
        cmd = [
            self._get_juju_binary(),
            "wait-for",
            "application",
            "-m",
            "admin/controller",
            "controller",
            "--timeout",
            "15m",
        ]
        self.update_status(status, "scaling controller")
        LOG.debug("Waiting for HA to be enabled")
        LOG.debug(f'Running command {" ".join(cmd)}')
        process = subprocess.run(
            cmd, capture_output=True, text=True, check=True
        )
        LOG.debug(
            f"Command finished. stdout={process.stdout}, stderr={process.stderr}"
        )
        return Result(ResultType.COMPLETED)
