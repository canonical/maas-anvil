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
import sys

import click
from rich.console import Console
from sunbeam.commands.juju import JujuLoginStep
from sunbeam.jobs.common import run_plan, run_preflight_checks
from sunbeam.plugins.interface.v1.base import PluginError

from anvil.jobs.checks import VerifyBootstrappedCheck
import anvil.provider
from anvil.provider.local.deployment import LocalDeployment

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


@click.command()
@click.pass_context
def juju_login(ctx: click.Context) -> None:
    """Login to the anvil controller."""
    deployment: LocalDeployment = ctx.obj()
    client = deployment.get_client()
    console = Console()

    preflight_checks = [VerifyBootstrappedCheck(client)]
    run_preflight_checks(preflight_checks, console)

    run_plan([JujuLoginStep(deployment.juju_account)], console)

    console.print("Juju login complete.")
