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

import datetime
import logging
from pathlib import Path
import shutil
import tarfile
import tempfile

import click
from rich.console import Console
from snaphelpers import Snap
from sunbeam.commands.juju import WriteCharmLogStep, WriteJujuStatusStep
from sunbeam.jobs.common import (
    run_plan,
    run_preflight_checks,
)
from sunbeam.jobs.deployment import Deployment
from sunbeam.jobs.juju import JujuHelper

from anvil.jobs.checks import DaemonGroupCheck

LOG = logging.getLogger(__name__)
console = Console()
snap = Snap()


@click.group(invoke_without_command=True)
@click.pass_context
def inspect(ctx: click.Context) -> None:
    """Inspect the maas-anvil installation.

    This script will inspect your installation. It will report any issue
    it finds, and create a tarball of logs and traces which can be
    attached to an issue filed against the maas-anvil project.
    """
    preflight_checks = []
    preflight_checks.append(DaemonGroupCheck())
    run_preflight_checks(preflight_checks, console)

    if ctx.invoked_subcommand is not None:
        return
    deployment: Deployment = ctx.obj
    jhelper = JujuHelper(deployment.get_connected_controller())

    time_stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"maas-anvil-inspection-report-{time_stamp}.tar.gz"
    dump_file: Path = Path(snap.paths.user_common) / file_name

    plan = []
    with tempfile.TemporaryDirectory() as tmpdirname:
        status_file = (
            Path(tmpdirname)
            / f"juju_status_{deployment.infrastructure_model}.out"
        )
        debug_file = (
            Path(tmpdirname)
            / f"debug_log_{deployment.infrastructure_model}.out"
        )
        plan.extend(
            [
                WriteJujuStatusStep(
                    jhelper, deployment.infrastructure_model, status_file
                ),
                WriteCharmLogStep(
                    jhelper, deployment.infrastructure_model, debug_file
                ),
            ]
        )

        run_plan(plan, console)

        with console.status("[bold green]Copying logs..."):
            log_dir = snap.paths.user_common / "logs"
            if log_dir.exists():
                shutil.copytree(log_dir, Path(tmpdirname) / "logs")

        with (
            console.status("[bold green]Creating tarball..."),
            tarfile.open(dump_file, "w:gz") as tar,
        ):
            tar.add(tmpdirname, arcname="./")

    console.print(f"[green]Output file written to {dump_file}[/green]")
