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

import inspect
import logging
import sys

import click
from sunbeam.plugins.interface.v1.base import PluginError

LOG = logging.getLogger(__name__)
LOCAL_ACCESS = "local"
REMOTE_ACCESS = "remote"


class EpilogFormatterMixin:
    """Mixin class for formatting epilogs with examples."""

    def format_epilog(
        self, ctx: click.Context, formatter: click.HelpFormatter
    ) -> None:
        """Writes the epilog into the formatter if it exists."""
        # We need to overwrite the default behaviour because otherwise
        # the whole Example block would be indented.
        if self.epilog:
            epilog = inspect.cleandoc(self.epilog)
            formatter.write_paragraph()
            formatter.write_heading("Example")

            with formatter.indentation():
                formatter.write_text(epilog)


# Create command version using the mixin
class FormatEpilogCommand(EpilogFormatterMixin, click.Command):
    """Click command that formats the epilog."""

    pass


class CatchGroup(EpilogFormatterMixin, click.Group):
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


class FormatCommandGroupsGroup(click.Group):
    """Format the commands in the root command into groups
    for better learnability.
    """

    def format_commands(
        self, ctx: click.Context, formatter: click.HelpFormatter
    ):
        commandGroups = [
            (
                "Prepare, create and manage a cluster",
                [
                    ("prepare-node-script", None),
                    ("cluster", lambda cmd: cmd.name != "list"),
                ],
            ),
            (
                "Configure and update the cluster",
                [
                    ("manifest", lambda _: True),
                    ("refresh", None),
                ],
            ),
            (
                "Monitor and debug the cluster",
                [
                    ("cluster", lambda cmd: cmd.name == "list"),
                    ("inspect", None),
                ],
            ),
            (
                "Manage a deployment",
                [
                    ("juju-login", None),
                ],
            ),
        ]

        # First pass: collect all commands and find the longest one
        # so we can later apply appropriate padding so table columns
        # are alligned across tables
        all_commands = []
        for _, filters in commandGroups:
            for cmd_name, filter_fn in filters:
                cmd = self.commands.get(cmd_name)
                if not cmd:
                    continue

                if filter_fn is None:
                    all_commands.append(cmd.name)
                elif isinstance(
                    cmd, click.Group
                ):  # Type check for subcommands
                    for subcmd in cmd.commands.values():
                        if filter_fn(subcmd):
                            all_commands.append(f"{cmd.name} {subcmd.name}")

        max_length = (
            max(len(cmd) for cmd in all_commands) if all_commands else 0
        )

        # Click by default has no concept of groups so we need to generate them ourselfs
        with formatter.section("Commands"):
            first = True

            for title, filters in commandGroups:
                # We don't want a newline for the first command group
                if first:
                    first = False
                else:
                    formatter.write_paragraph()

                formatter.write_heading(click.style(title, underline=True))
                formatter.indent()
                # Collect commands for this group
                group_commands = []
                for cmd_name, filter_fn in filters:
                    cmd = self.commands.get(cmd_name)
                    if not cmd:
                        continue

                    if filter_fn is None:
                        group_commands.append(
                            (
                                cmd.name.ljust(max_length),
                                cmd.get_short_help_str(75),
                            )
                    elif isinstance(
                        cmd, click.Group
                    ):  # Type check for subcommands
                        for subcmd in cmd.commands.values():
                            if filter_fn(subcmd):
                                group_commands.append(
                                    (
                                        f"{cmd.name} {subcmd.name}".ljust(
                                            max_length
                                        ),
                                        subcmd.get_short_help_str(75),
                                    )
                                )

                formatter.write_dl(
                    group_commands, col_max=max_length, col_spacing=2
                )
                formatter.dedent()
