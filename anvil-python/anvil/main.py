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

import click
from snaphelpers import Snap
from sunbeam import log
from sunbeam.commands import (
    configure as configure_cmds,
)
from sunbeam.utils import CatchGroup

from anvil.commands import (
    manifest as manifest_commands,
    prepare_node as prepare_node_cmds,
)
from anvil.provider.local.commands import LocalProvider
from anvil.provider.local.deployment import LocalDeployment

# Update the help options to allow -h in addition to --help for
# triggering the help for various commands
CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.group("init", context_settings=CONTEXT_SETTINGS, cls=CatchGroup)
@click.option("--quiet", "-q", default=False, is_flag=True)
@click.option("--verbose", "-v", default=False, is_flag=True)
@click.pass_context
def cli(ctx: click.Context, quiet: bool, verbose: bool) -> CatchGroup:
    """Anvil is a MAAS installer for MAAS charms.

    To get started with a single node, all-in-one MAAS installation, start
    with by initializing the local node. Once the local node has been initialized,
    run the bootstrap process to get a live MAAS deployment.
    """


@click.group("manifest", context_settings=CONTEXT_SETTINGS, cls=CatchGroup)
@click.pass_context
def manifest(ctx: click.Context) -> None:
    """Manage manifests (read-only commands)"""


def main() -> None:
    snap = Snap()
    logfile = log.prepare_logfile(snap.paths.user_common / "logs", "sunbeam")
    log.setup_root_logging(logfile)
    cli.add_command(prepare_node_cmds.prepare_node_script)

    # Cluster management
    deployment = LocalDeployment()
    provider = LocalProvider()
    provider.register_cli(cli, configure_cmds.configure, deployment)

    # Manifest management
    cli.add_command(manifest)
    manifest.add_command(manifest_commands.list)
    manifest.add_command(manifest_commands.show)
    manifest.add_command(manifest_commands.generate)

    cli(obj=deployment)


if __name__ == "__main__":
    main()
