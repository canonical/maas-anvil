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
import os
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from sunbeam.clusterd.service import (
    ClusterServiceUnavailableException,
    ManifestItemNotFoundException,
)
from sunbeam.jobs.common import FORMAT_TABLE, FORMAT_YAML, run_preflight_checks
from sunbeam.jobs.deployment import Deployment
from sunbeam.utils import asdict_with_extra_fields
import yaml

from anvil.jobs.checks import DaemonGroupCheck, VerifyBootstrappedCheck
from anvil.jobs.manifest import Manifest
from anvil.utils import FormatEpilogCommand

LOG = logging.getLogger(__name__)
console = Console()


def generate_software_manifest(manifest: Manifest) -> str:
    space = " "
    indent = space * 2
    comment = "# "

    try:
        software_dict = asdict_with_extra_fields(manifest.software_config)
        LOG.debug(f"Manifest software dict with extra fields: {software_dict}")

        # Remove terraform default sources
        manifest_terraform_dict = software_dict.get("terraform", {})
        for name, value in manifest_terraform_dict.items():
            if value.get("source") and value.get("source").startswith(
                "/snap/anvil"
            ):
                value["source"] = None

        software_yaml = yaml.safe_dump(software_dict, sort_keys=False)

        # TODO(hemanth): Add an option schema to print the JsonSchema for the
        # Manifest. This will be easier when moved to pydantic 2.x

        # add comment to each line
        software_lines = (
            f"{indent}{comment}{line}" for line in software_yaml.split("\n")
        )
        software_yaml_commented = "\n".join(software_lines)
        software_content = f"software:\n{software_yaml_commented}"
        return software_content
    except Exception as e:
        LOG.debug(e)
        raise click.ClickException(f"Manifest generation failed: {e!s}")


@click.command(
    cls=FormatEpilogCommand,
    epilog="""
    \b
    List previously used manifest files.
    maas-anvil manifest list
    """,
)
@click.option(
    "-f",
    "--format",
    type=click.Choice([FORMAT_TABLE, FORMAT_YAML]),
    default=FORMAT_TABLE,
    help="Output format of the list.",
)
@click.pass_context
def list(ctx: click.Context, format: str) -> None:
    """Lists manifest files that were used in the cluster."""
    deployment: Deployment = ctx.obj
    client = deployment.get_client()
    manifests = []

    preflight_checks = [DaemonGroupCheck()]
    run_preflight_checks(preflight_checks, console)

    try:
        manifests = client.cluster.list_manifests()
    except ClusterServiceUnavailableException:
        click.echo("Error: Not able to connect to Cluster DB")
        return

    if format == FORMAT_TABLE:
        table = Table()
        table.add_column("ID", justify="left")
        table.add_column("Applied Date", justify="left")
        for manifest in manifests:
            table.add_row(
                manifest.get("manifestid"), manifest.get("applieddate")
            )
        console.print(table)
    elif format == FORMAT_YAML:
        for manifest in manifests:
            manifest.pop("data")
        click.echo(yaml.dump(manifests))


@click.command(
    cls=FormatEpilogCommand,
    epilog="""
    \b
    Show the contents of the most recently committed manifest file.
    maas-anvil manifest show --id=latest
    """,
)
@click.option(
    "--id", type=str, prompt=True, help="The database id of the manifest file."
)
@click.pass_context
def show(ctx: click.Context, id: str) -> None:
    """Shows the contents of a manifest file given an id.
    Get ids using the 'manifest list' command. Use '--id=latest' to show the most
    recently committed manifest.
    """
    deployment: Deployment = ctx.obj
    client = deployment.get_client()

    preflight_checks = [DaemonGroupCheck()]
    run_preflight_checks(preflight_checks, console)

    try:
        manifest = client.cluster.get_manifest(id)
        click.echo(manifest.get("data"))
    except ClusterServiceUnavailableException:
        click.echo("Error: Not able to connect to Cluster DB")
    except ManifestItemNotFoundException:
        click.echo(f"Error: No manifest exists with id {id}")


@click.command(
    cls=FormatEpilogCommand,
    epilog="""
    \b
    Generate a manifest file with (default) configuration to be saved in the default
    location of '$HOME/.config/anvil/manifest.yaml'
    maas-anvil manifest generate
    """,
)
@click.option(
    "-o",
    "--output",
    help="Output file for manifest, defaults to $HOME/.config/anvil/manifest.yaml",
    type=click.Path(dir_okay=False, path_type=Path),
)
@click.pass_context
def generate(
    ctx: click.Context,
    output: Path | None = None,
) -> None:
    """Generates a manifest file. Either with the configuration of the currently deployed
    MAAS Anvil cluster or, if no cluster was bootstrapped yet, a default configuration.
    """
    deployment: Deployment = ctx.obj

    if not output:
        home = os.environ.get("SNAP_REAL_HOME", "")
        output = Path(home) / ".config" / "anvil" / "manifest.yaml"

    LOG.debug(f"Creating {output} parent directory if it does not exist")
    output.parent.mkdir(mode=0o775, parents=True, exist_ok=True)

    try:
        client = deployment.get_client()
        preflight_checks = [
            DaemonGroupCheck(),
            VerifyBootstrappedCheck(client),
        ]
        run_preflight_checks(preflight_checks, console)
        manifest_obj = Manifest.load_latest_from_clusterdb(
            deployment, include_defaults=True
        )
    except (
        click.ClickException,
        ClusterServiceUnavailableException,
        ValueError,
    ):
        LOG.debug(
            "Fallback to generating manifest with defaults", exc_info=True
        )
        manifest_obj = Manifest.get_default_manifest(deployment)

    preseed_content = deployment.generate_preseed(console)
    software_content = generate_software_manifest(manifest_obj)

    try:
        with output.open("w") as file:
            file.write("# Generated Anvil Deployment Manifest\n\n")
            file.write(preseed_content)
            file.write("\n")
            file.write(software_content)
    except OSError as e:
        LOG.debug(e)
        raise click.ClickException(f"Manifest generation failed: {e!s}")

    click.echo(f"Generated manifest is at {output!s}")
