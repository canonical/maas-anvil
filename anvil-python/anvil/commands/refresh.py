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
from pathlib import Path

import click
from rich.console import Console
from sunbeam.jobs.common import (
    run_plan,
)
from sunbeam.jobs.juju import JujuHelper
import yaml

from anvil.commands.upgrades.inter_channel import ChannelUpgradeCoordinator
from anvil.commands.upgrades.intra_channel import LatestInChannelCoordinator
from anvil.jobs.manifest import AddManifestStep, Manifest
from anvil.provider.local.deployment import LocalDeployment
from anvil.utils import FormatEpilogCommand

LOG = logging.getLogger(__name__)
console = Console()


@click.command(
    cls=FormatEpilogCommand,
    epilog="""
    \b
    Refresh the MAAS Anvil cluster.
    maas-anvil refresh
    """,
)
@click.option(
    "-m",
    "--manifest",
    "manifest_path",
    help=(
        "If provided, the cluster is refreshed with the configuration "
        "specified in the manifest file."
    ),
    type=click.Path(
        exists=True, dir_okay=False, path_type=Path, allow_dash=True
    ),
)
@click.option(
    "-u",
    "--upgrade-release",
    is_flag=True,
    show_default=True,
    default=False,
    help=(
        "Allows charm upgrades if the new manifest specifies charms in channels "
        "with higher tracks than the current one."
    ),
)
@click.pass_context
def refresh(
    ctx: click.Context,
    manifest_path: Path | None = None,
    upgrade_release: bool = False,
) -> None:
    """Updates all charms within their current channel.
    A manifest file can be passed to refresh the deployment with
    new configuration.
    """

    deployment: LocalDeployment = ctx.obj
    client = deployment.get_client()

    manifest = None
    if manifest_path:
        try:
            with click.open_file(manifest_path) as file:  # type: ignore
                manifest_data = yaml.safe_load(file)
        except (OSError, yaml.YAMLError) as e:
            LOG.debug(e)
            raise click.ClickException(f"Manifest parsing failed: {e!s}")

        manifest = Manifest.load(
            deployment,
            manifest_data=manifest_data or {},
            include_defaults=True,
        )
        run_plan([AddManifestStep(client, manifest_data)], console)

    if not manifest:
        LOG.debug("Getting latest manifest from cluster db")
        manifest = Manifest.load_latest_from_clusterdb(
            deployment, include_defaults=True
        )

    LOG.debug(
        f"Manifest used for refresh - deployment preseed: {manifest.deployment_config}"
    )
    LOG.debug(
        f"Manifest used for refresh - software: {manifest.software_config}"
    )
    jhelper = JujuHelper(deployment.get_connected_controller())

    coordinator = (
        ChannelUpgradeCoordinator(
            deployment,
            client,
            jhelper,
            manifest,
        )
        if upgrade_release
        else LatestInChannelCoordinator(
            deployment,
            client,
            jhelper,
            manifest,
        )
    )
    upgrade_plan = coordinator.get_plan()  # type:ignore [attr-defined]
    run_plan(upgrade_plan, console)

    click.echo("Refresh complete.")
