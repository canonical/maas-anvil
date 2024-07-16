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
import subprocess
import sys
from typing import Any

import click
from sunbeam.plugins.interface.v1.base import PluginError

from anvil.jobs.juju import CONTROLLER

LOG = logging.getLogger(__name__)
LOCAL_ACCESS = "local"
REMOTE_ACCESS = "remote"


class CatchGroup(click.Group):
    """Catch exceptions and print them to stderr."""

    def __call__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        try:
            return self.main(*args, **kwargs)
        except PluginError as e:
            LOG.debug(e, exc_info=True)
            LOG.error("Error: %s", e)
            sys.exit(1)
        except Exception as e:
            LOG.debug(e, exc_info=True)
            message = (
                "An unexpected error has occurred."
                " Please run 'maas-anvil inspect' to generate an inspection report."
            )
            LOG.warn(message)
            LOG.error("Error: %s", e)
            sys.exit(1)

def get_all_machines() -> dict[str: Any]:
    machines_res = subprocess.run(
            ["juju", "machines", "--format", "json"], capture_output=True
        )
    return json.loads(machines_res.stdout)["machines"]


def machines_missing_juju_controllers() -> list[str]:
    result = subprocess.run(
        ["juju", "show-controller", CONTROLLER, "--format", "json"],
        capture_output=True,
    )
    controllers = json.loads(result.stdout)
    controller_machines = set(
        controllers[CONTROLLER]["controller-machines"].keys()
    )

    machines_res = subprocess.run(
        ["juju", "machines", "--format", "json"], capture_output=True
    )
    machines = set(json.loads(machines_res.stdout)["machines"].keys())
    return list(machines.difference(controller_machines))
