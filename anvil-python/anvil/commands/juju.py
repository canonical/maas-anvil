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
import subprocess

from rich.status import Status
from sunbeam.commands.juju import (
    RemoveJujuMachineStep as SunbeamRemoveJujuMachineStep,
)
from sunbeam.jobs.common import BaseStep, Result, ResultType
from sunbeam.jobs.juju import CONTROLLER_MODEL

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


class RemoveJujuMachineStep(SunbeamRemoveJujuMachineStep):
    def run(self, status: Status | None = None) -> Result:
        try:
            if self.machine_id == -1:
                return Result(
                    ResultType.FAILED,
                    "Not able to retrieve machine id from Cluster database",
                )

            cmd = [
                self._get_juju_binary(),
                "remove-machine",
                "-m",
                CONTROLLER_MODEL,
                str(self.machine_id),
                "--no-prompt",
            ]
            LOG.debug(f'Running command {" ".join(cmd)}')
            process = subprocess.run(
                cmd, capture_output=True, text=True, check=True
            )
            LOG.debug(
                f"Command finished. stdout={process.stdout}, stderr={process.stderr}"
            )
        except subprocess.CalledProcessError as e:
            # Despite the is_skip identified that machine is present in the model there
            # is chance that when remove-machine invocation happens, the machine has already
            # gone. This can happen since the machine is auto-removed if there is no unit of
            # any application, including controller, deployed on it.
            if f"machine {self.machine_id} not found" in e.stderr:
                return Result(ResultType.COMPLETED)

            LOG.exception(
                f"Error removing machine {self.machine_id} from Juju"
            )
            LOG.warning(e.stderr)
            return Result(ResultType.FAILED, str(e))

        try:
            cmd = [
                self._get_juju_binary(),
                "wait-for",
                "machine",
                "-m",
                CONTROLLER_MODEL,
                str(self.machine_id),
                "--query",
                'life=="dead"',
            ]
            LOG.debug(f'Running command {" ".join(cmd)}')
            process = subprocess.run(
                cmd, capture_output=True, text=True, check=True
            )
            LOG.debug(
                f"Command finished. stdout={process.stdout}, stderr={process.stderr}"
            )
        except subprocess.CalledProcessError as e:
            # wait-for does not support cases when the machine was not found with the initial query.
            # In cases where the machine is removed before waiting-for its removal, the wait-for
            # will timeout waiting. We need to check that in case of failure the machine could not
            # be found from the beginning.
            if e.stderr.startswith(
                f'machine "{self.machine_id}" not found, waiting'
            ):
                LOG.debug("Machine was removed before waiting for it")
                return Result(ResultType.COMPLETED)
            LOG.exception(
                f"Error waiting for removal of machine {self.machine_id} from Juju"
            )
            LOG.warning(e.stderr)
            return Result(ResultType.FAILED, str(e))

        return Result(ResultType.COMPLETED)
