import logging
from pathlib import Path

import click
from rich.console import Console
from sunbeam.jobs.common import (
    run_plan,
)
from sunbeam.jobs.juju import JujuHelper
from sunbeam.jobs.manifest import AddManifestStep

from anvil.commands.upgrades.intra_channel import LatestInChannelCoordinator
from anvil.jobs.manifest import Manifest
from anvil.provider.local.deployment import LocalDeployment

LOG = logging.getLogger(__name__)
console = Console()


@click.command()
@click.option(
    "-m",
    "--manifest",
    "manifest_path",
    help="Manifest file.",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.pass_context
def refresh(
    ctx: click.Context,
    manifest_path: Path | None = None,
) -> None:
    """Refresh deployment.

    Refresh the deployment and allow passing new configuration options.
    """

    deployment: LocalDeployment = ctx.obj
    client = deployment.get_client()

    manifest = None
    if manifest_path:
        manifest = Manifest.load(
            deployment, manifest_file=manifest_path, include_defaults=True
        )
        run_plan([AddManifestStep(client, manifest)], console)

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

    a = LatestInChannelCoordinator(
        deployment,
        client,
        jhelper,
        manifest,
    )
    a.run_plan()

    click.echo("Refresh complete.")
