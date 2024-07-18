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

from os import environ
import os.path
import subprocess

from rich.status import Status
from sunbeam.jobs.common import BaseStep, Result, ResultType


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
