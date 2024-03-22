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
import pathlib
from pathlib import Path
import sys

import click
from rich.console import Console
from rich.table import Table
from snaphelpers import Snap
from sunbeam.jobs.checks import LocalShareCheck
from sunbeam.jobs.common import (
    CONTEXT_SETTINGS,
    FORMAT_TABLE,
    FORMAT_YAML,
    run_plan,
    run_preflight_checks,
)
from sunbeam.jobs.deployment import Deployment, register_deployment_type
from sunbeam.jobs.deployments import (
    DeploymentsConfig,
    deployment_path,
    list_deployments,
    store_deployment_as_yaml,
)
from sunbeam.provider.base import ProviderBase
from sunbeam.utils import CatchGroup
import yaml

from anvil.provider.local.commands import LocalProvider
from anvil.provider.local.deployment import LocalDeployment

console = Console()
LOG = logging.getLogger(__name__)


def load_deployment(path: Path) -> Deployment:
    """Load deployment automatically."""
    if not path.exists():
        return LocalDeployment()

    deployments = DeploymentsConfig.load(path)

    if deployments.active is None:
        LOG.debug("No active deployment found.")
        return LocalDeployment()

    return deployments.get_active()


def register_providers() -> None:
    """Auto-register providers."""
    providers: list[ProviderBase] = [LocalProvider()]
    for provider_obj in providers:
        deployment_type = provider_obj.deployment_type()
        if deployment_type:
            LOG.debug("Registering deployment type: %s", deployment_type)
            register_deployment_type(*deployment_type)


@click.group("deployment", context_settings=CONTEXT_SETTINGS, cls=CatchGroup)
@click.pass_context
def deployment_group(ctx: click.Context) -> None:
    """Manage deployments."""
    pass


@deployment_group.group(  # type: ignore[misc]
    "add", context_settings=CONTEXT_SETTINGS, cls=CatchGroup
)
@click.pass_context
def add(ctx: click.Context) -> None:
    """Add a deployment."""
    pass


@deployment_group.command()  # type: ignore[misc]
@click.argument("name", type=str)
def switch(name: str) -> None:
    """Switch deployment."""
    preflight_checks = [
        LocalShareCheck(),
    ]
    run_preflight_checks(preflight_checks, console)

    snap = Snap()
    path = deployment_path(snap)
    deployments_config = DeploymentsConfig.load(path)
    try:
        deployments_config.switch(name)
        click.echo(f"Deployment switched to {name}.")
    except ValueError as e:
        click.echo(str(e))
        sys.exit(1)


@deployment_group.command("import")  # type: ignore[misc]
@click.option(
    "--file",
    type=click.Path(exists=True, path_type=pathlib.Path),
    help="Deployment file",
)
def import_deployment(file: Path | None) -> None:
    """Import deployment."""
    if file is None:
        click.echo("Missing deployment file argument.")
        sys.exit(1)
    preflight_checks = [
        LocalShareCheck(),
    ]
    run_preflight_checks(preflight_checks, console)

    # try parsing the deployment
    deployment_yaml = yaml.safe_load(file.read_text())
    try:
        deployment = Deployment.load(deployment_yaml)
    except ValueError as e:
        click.echo(str(e))
        sys.exit(1)

    import_step_class = deployment.import_step()

    if import_step_class is NotImplemented:
        click.echo(
            f"Import not supported for deployment type {deployment.type}."
        )
        sys.exit(1)

    snap = Snap()
    path = deployment_path(snap)
    try:
        deployments_config = DeploymentsConfig.load(path)
    except ValueError as e:
        click.echo(str(e))
        sys.exit(1)

    plan = []
    plan.append(import_step_class(deployments_config, deployment))

    run_plan(plan, console)

    console.print(f"Deployment {deployment.name!r} imported.")


@deployment_group.command("export")  # type: ignore[misc]
@click.argument("name", type=str)
def export_deployment(name: str) -> None:
    """Export deployment."""
    preflight_checks = [
        LocalShareCheck(),
    ]
    run_preflight_checks(preflight_checks, console)

    snap = Snap()
    path = deployment_path(snap)
    try:
        deployments_config = DeploymentsConfig.load(path)
        deployment = deployments_config.get_deployment(name)
        stored_path = store_deployment_as_yaml(snap, deployment)
    except ValueError as e:
        click.echo(str(e))
        sys.exit(1)

    console.print(f"Deployment exported to {str(stored_path)!r}")


@deployment_group.command("list")  # type: ignore[misc]
@click.option(
    "--format",
    type=click.Choice([FORMAT_TABLE, FORMAT_YAML]),
    default=FORMAT_TABLE,
    help="Output format",
)
def list_providers(format: str) -> None:
    """List OpenStack deployments."""
    preflight_checks = [
        LocalShareCheck(),
    ]
    run_preflight_checks(preflight_checks, console)

    snap = Snap()
    path = deployment_path(snap)
    deployments_config = DeploymentsConfig.load(path)
    deployment_list = list_deployments(deployments_config)
    if format == FORMAT_TABLE:
        table = Table()
        table.add_column("Deployment")
        table.add_column("Endpoint")
        table.add_column("Type")
        for deployment in deployment_list["deployments"]:
            style = None
            name = deployment["name"]
            url = deployment["url"]
            type = deployment["type"]
            if name == deployment_list["active"]:
                name = name + "*"
                style = "green"
            table.add_row(name, url, type, style=style)
        console.print(table)
    elif format == FORMAT_YAML:
        console.print(yaml.dump(deployment_list), end="")


@deployment_group.command()  # type: ignore[misc]
@click.argument("name", type=str)
@click.option(
    "--format",
    type=click.Choice([FORMAT_TABLE, FORMAT_YAML]),
    default=FORMAT_TABLE,
    help="Output format",
)
def show(name: str, format: str) -> None:
    """Show deployment detail."""
    preflight_checks = [
        LocalShareCheck(),
    ]
    run_preflight_checks(preflight_checks, console)

    snap = Snap()
    path = deployment_path(snap)
    deployments_config = DeploymentsConfig.load(path)
    try:
        deployment = deployments_config.get_deployment(name)
    except ValueError as e:
        click.echo(str(e))
        sys.exit(1)
    if format == FORMAT_TABLE:
        table = Table(show_header=False)
        for header, value in deployment.dict().items():
            table.add_row(f"[bold]{header.capitalize()}[/bold]", str(value))
        console.print(table)
    elif format == FORMAT_YAML:
        console.print(yaml.dump(deployment), end="")


def register_cli(
    cli: click.Group, configure: click.Group, deployment: Deployment
) -> None:
    """Register the CLI for the given provider."""
    cli.add_command(deployment_group)
    providers: list[ProviderBase] = [
        LocalProvider(),
    ]
    for provider_obj in providers:
        provider_obj.register_add_cli(add)
        type_name, type_cls = provider_obj.deployment_type()
        if isinstance(deployment, type_cls):
            LOG.debug(
                "Registering deployment type %r of cls %r",
                type_name,
                type_cls,
            )
            provider_obj.register_cli(cli, configure, deployment_group)
