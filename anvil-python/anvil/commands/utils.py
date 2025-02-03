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
import re
import subprocess

import click
from rich.console import Console
from sunbeam.commands.juju import JujuLoginStep
from sunbeam.jobs.common import run_plan, run_preflight_checks

from anvil.jobs.checks import VerifyBootstrappedCheck
from anvil.provider.local.deployment import LocalDeployment
from anvil.utils import FormatEpilogCommand

LOG = logging.getLogger(__name__)
console = Console()


@click.command(
    cls=FormatEpilogCommand,
    epilog="""
    \b
    Log into the Juju controller to manually interact with the Juju controller created
    by MAAS Anvil.
    maas-anvil juju-login
    """,
)
@click.pass_context
def juju_login(ctx: click.Context) -> None:
    """Logs into the Juju controller used by MAAS Anvil.
    The login is performed using the current host user.
    """
    deployment: LocalDeployment = ctx.obj
    run_preflight_checks(
        [VerifyBootstrappedCheck(deployment.get_client())], console
    )
    run_plan([JujuLoginStep(deployment.juju_account)], console)

    console.print("Juju re-login complete.")


def validate_ssh_import(
    ctx: click.core.Context, param: click.core.Option, value: str | None
) -> str | None:
    if value and re.fullmatch("(lp|gh):.+", value) is None:
        raise click.BadParameter(
            "--ssh-import must be of the form 'lp:username' or 'gh:username'",
            ctx,
        )
    return value


@click.command(
    cls=FormatEpilogCommand,
    epilog="""
    \b
    Create a MAAS admin account with the following details:
    Username: admin
    Password: VerySecure9000
    Email: admin@company.com
    Launchpad account to import SSH key from: lp-username
    \b
    maas-anvil create-admin --username admin --password VerySecure9000 --email admin@company.com --ssh-import lp:lp-username""",
)
@click.option(
    "--username",
    help="The username for the new admin account",
    required=True,
)
@click.option(
    "--password",
    help="The password for the new admin account",
    required=True,
)
@click.option(
    "--email",
    help="The email address for the new admin account",
    required=True,
)
@click.option(
    "--ssh-import",
    help="Import SSH keys from Launchpad (lp:user-id) or GitHub (gh:user-id)",
    callback=validate_ssh_import,
)
@click.pass_context
def create_admin(
    ctx: click.Context,
    username: str,
    password: str,
    email: str,
    ssh_import: str | None,
) -> None:
    """Creates a MAAS admin account."""
    cmd = [
        "juju",
        "run",
        "maas-region/0",
        "create-admin",
        f"username={username}",
        f"password={password}",
        f"email={email}",
    ]
    if ssh_import:
        cmd.append(f"ssh-import={ssh_import}")
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Failed to create MAAS admin account: {e.stderr.decode()}"
        )
    console.print("MAAS admin account has been successfully created.")
