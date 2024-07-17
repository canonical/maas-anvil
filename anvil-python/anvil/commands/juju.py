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

import json
import logging
from os import environ
import os.path
import subprocess

from rich.status import Status

from sunbeam.commands.juju import JujuStepHelper
from sunbeam.jobs.common import BaseStep, Result, ResultType

from anvil.utils import machines_missing_juju_controllers

LOG = logging.getLogger(__name__)


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


class ScaleUpJujuStep(BaseStep, JujuStepHelper):
    """Enable Juju HA."""

    def __init__(
        self, controller: str, n: int = 3, extra_args: list[str] | None = None
    ):
        super().__init__("Juju HA", "Enable Juju High Availability")
        self.controller = controller
        self.n = n
        self.extra_args = extra_args or []

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

    def is_skip(self, status: Status | None = None) -> Result:
        """Determines if the step should be skipped or not."""
        machines_res = subprocess.run(
            ["juju", "machines", "--format", "json"], capture_output=True
        )
        machines = json.loads(machines_res.stdout)["machines"]
        n_machines = len(machines)
        if n_machines > 2 and n_machines <= 7 and n_machines % 2 == 1:
            machines_to_join = machines_missing_juju_controllers()
            self.n = n_machines
            self.extra_args.extend(("--to", ",".join(machines_to_join)))
            LOG.debug(
                f"Will enable Juju controller on machines {machines_to_join}"
            )
            return Result(ResultType.COMPLETED)
        LOG.debug(
            "Number of machines must be odd and between 3 and 7 (inclusive), "
            "skipping scaling Juju controllers"
        )
        return Result(ResultType.SKIPPED)
