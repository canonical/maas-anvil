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

import enum
from typing import Any

import click

RAM_4_GB_IN_KB = 4 * 1000 * 1000


class Role(enum.Enum):
    """The role that the current node will play

    This determines if the role will be a region node, a rack/agent node,
    r database node or a haproxy node. The role will help determine which
    particular services need to be configured and installed on the system.
    """

    REGION = 1
    AGENT = 2
    DATABASE = 3
    HAPROXY = 4

    def is_region_node(self) -> bool:
        """Returns True if the node requires MAAS region services.

        :return: True if the node should have MAAS region services,
                 False otherwise
        """
        return self == Role.REGION

    def is_agent_node(self) -> bool:
        """Returns True if the node requires MAAS agent services.

        :return: True if the node should have MAAS agent services,
                 False otherwise
        """
        return self == Role.AGENT

    def is_database_node(self) -> bool:
        """Returns True if the node requires PostgreSQL service.

        :return: True if the node should have PostgreSQL service,
                 False otherwise
        """
        return self == Role.DATABASE

    def is_haproxy_node(self) -> bool:
        """Returns True if the node requires HAProxy service.

        :return: True if the node should have HAProxy service,
                 False otherwise
        """
        return self == Role.HAPROXY


def roles_to_str_list(roles: list[Role]) -> list[str]:
    return [role.name.lower() for role in roles]


def validate_roles(
    ctx: click.core.Context, param: click.core.Option, value: tuple[Any]
) -> list[Role]:
    try:
        return [Role[role.upper()] for role in value]
    except KeyError as e:
        raise click.BadParameter(str(e))
