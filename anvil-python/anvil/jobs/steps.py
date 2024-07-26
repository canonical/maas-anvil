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
from sunbeam.commands.juju import JujuStepHelper
from sunbeam.jobs.common import Result, ResultType
from sunbeam.jobs.juju import CONTROLLER_MODEL
from sunbeam.jobs.steps import (
    RemoveMachineUnitStep as SunbeamRemoveMachineUnitStep,
)

LOG = logging.getLogger(__name__)


class RemoveMachineUnitStep(SunbeamRemoveMachineUnitStep, JujuStepHelper):
    def run(self, status: Status | None = None) -> Result:
        res = super().run(status)
        if res.result_type != ResultType.COMPLETED:
            return res
        try:
            cmd = [
                self._get_juju_binary(),
                "wait-for",
                "unit",
                "-m",
                CONTROLLER_MODEL,
                self.unit,
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
            # wait-for does not support cases when the unit was not found with the initial query.
            # In cases where the unit is removed before waiting-for its removal, the wait-for
            # will timeout waiting. We need to check that in case of failure the unit could not
            # be found from the beginning.
            if e.stderr.startswith(f'unit "{self.unit}" not found, waiting'):
                LOG.debug("Unit was removed before waiting for it")
                return Result(ResultType.COMPLETED)
            LOG.exception(
                f"Error waiting for removal of unit {self.unit} from Juju"
            )
            LOG.warning(e.stderr)
            return Result(ResultType.FAILED, str(e))

        return Result(ResultType.COMPLETED)
