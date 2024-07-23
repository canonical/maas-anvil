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
from os import environ
import os.path
import random
import subprocess

from rich.status import Status
from sunbeam.commands.juju import JujuStepHelper
from sunbeam.jobs.common import BaseStep, Result, ResultType
from sunbeam.jobs.juju import JujuHelper, run_sync

from anvil.jobs.juju import CONTROLLER

LOG = logging.getLogger(__name__)
MAX_JUJU_CONTROLLERS = 3


class JujuAddSSHKeyStep(BaseStep):
    """Add this node's SSH key to the Juju model"""

    def __init__(self) -> None:
        super().__init__("Add SSH key", "Adding SSH key to Juju model")

    def run(self, status: Status | None) -> Result:
        try:
            with open(
                os.path.join(
                    f"{environ['SNAP_REAL_HOME']}", ".ssh/id_rsa.pub"
                ),
            ) as f:
                key = f.read().removesuffix(
                    "\n"
                )  # juju does not like this newline
                cmd = ["juju", "add-ssh-key", key]
                result = subprocess.run(
                    cmd,
                    check=True,
                    capture_output=True,
                )
        except subprocess.CalledProcessError:
            return Result(
                ResultType.FAILED,
                message=f"juju add-ssh-key failed: {result.stderr.decode('utf-8', errors='ignore')}",
            )
        except FileNotFoundError:
            return Result(
                ResultType.FAILED,
                message="Could not find public ssh key (~/.ssh/id_rsa.pub)",
            )
        return Result(ResultType.COMPLETED)


class ScaleJujuStep(BaseStep, JujuStepHelper):
    """Enable Juju HA."""

    def __init__(
        self,
        jhelper: JujuHelper,
        model: str,
    ):
        super().__init__("Juju HA", "Enable Juju High Availability")

        self.jhelper = jhelper
        self.model = model

        self.controller_machines: set[str] = set()
        self.machines: set[str] = set()

    def run(self, status: Status | None = None) -> Result:
        """Run the step to completion."""

        available_machines = list(self.machines ^ self.controller_machines)
        n_machines_to_join = min(
            len(available_machines),
            MAX_JUJU_CONTROLLERS - len(self.controller_machines),
        )

        cmd = [
            self._get_juju_binary(),
            "enable-ha",
            "-n",
            str(len(self.controller_machines) + n_machines_to_join),
            "--to",
            ",".join(
                str(s)
                for s in random.sample(available_machines, n_machines_to_join)
            ),
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

    def is_skip(self, status: Status | None = None) -> Result:
        """Determines if the step should be skipped or not."""

        self.controller_machines = set(
            self.get_controller(CONTROLLER)["controller-machines"].keys()
        )
        self.machines = set(
            run_sync(self.jhelper.get_machines(self.model)).keys()
        )
        available_machines = self.machines ^ self.controller_machines

        if len(self.controller_machines) == MAX_JUJU_CONTROLLERS:
            LOG.debug(
                "Number of machines with controllers must not be greater than "
                f"{MAX_JUJU_CONTROLLERS}, skipping scaling Juju controllers"
            )
            return Result(ResultType.SKIPPED)
        if len(available_machines) == 0:
            LOG.debug(
                "No available machines, skipping scaling Juju controllers"
            )
            return Result(ResultType.SKIPPED)
        if len(self.machines) < 3:
            LOG.debug("Number of machines must be at least 3")
            return Result(ResultType.SKIPPED)

        return Result(ResultType.COMPLETED)
