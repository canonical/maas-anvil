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
from typing import List

from sunbeam.clusterd.client import Client

LOG = logging.getLogger(__name__)

from sunbeam.commands.clusterd import (
    ClusterInitStep as SunbeamClusterInitStep,
    ClusterJoinNodeStep as SunbeamClusterJoinNodeStep,
    ClusterListNodeStep as SunbeamClusterListNodeStep,
    ClusterRemoveNodeStep as SunbeamClusterRemoveNodeStep,
)


class ClusterInitStep(SunbeamClusterInitStep):
    """Bootstrap clustering on Anvil clusterd."""

    def __init__(self, client: Client, role: List[str], machineid: int):
        super().__init__(client=client, role=role, machineid=machineid)

        self.name = "Bootstrap Cluster"
        self.description = "Bootstrapping Anvil cluster"


class ClusterJoinNodeStep(SunbeamClusterJoinNodeStep):
    """Join node to the Anvil cluster."""

    def __init__(self, client: Client, token: str, role: List[str]):
        super().__init__(client=client, token=token, role=role)

        self.name = "Join node to Cluster"
        self.description = "Adding node to Anvil cluster"


class ClusterListNodeStep(SunbeamClusterListNodeStep):
    """List nodes in the Anvil cluster."""

    def __init__(self, client: Client):
        super().__init__(client=client)

        self.name = "List nodes of Cluster"
        self.description = "Listing nodes in Anvil cluster"


class ClusterRemoveNodeStep(SunbeamClusterRemoveNodeStep):
    """Remove node from the Anvil cluster."""

    def __init__(self, client: Client, name: str):
        super().__init__(client=client, name=name)

        self.name = "Remove node from Cluster"
        self.description = "Removing node from Anvil cluster"
