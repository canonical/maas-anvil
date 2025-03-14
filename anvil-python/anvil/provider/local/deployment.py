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
from typing import Any

from rich.console import Console
from sunbeam.clusterd.service import (
    ClusterServiceUnavailableException,
)
from sunbeam.commands.juju import BOOTSTRAP_CONFIG_KEY, bootstrap_questions
from sunbeam.jobs.questions import QuestionBank, load_answers
from sunbeam.provider.local.deployment import (
    LocalDeployment as SunbeamLocalDeployment,
)

from anvil.commands.haproxy import (
    HAPROXY_CONFIG_KEY,
    HAPROXY_VALID_TLS_MODES,
    haproxy_questions,
    tls_questions,
)
from anvil.commands.maas_region import (
    MAAS_REGION_VALID_TLS_MODES,
    MAASREGION_CONFIG_KEY,
)
from anvil.commands.postgresql import (
    POSTGRESQL_CONFIG_KEY,
    postgresql_questions,
)
from anvil.jobs.questions import show_questions

LOG = logging.getLogger(__name__)
LOCAL_TYPE = "local"


class LocalDeployment(SunbeamLocalDeployment):
    def __init__(self, **data: Any) -> None:
        super().__init__(**data)

    def generate_preseed(self, console: Console) -> str:
        """Generate preseed for deployment."""
        client = self.get_client()
        preseed_content = ["deployment:"]
        try:
            variables = load_answers(client, BOOTSTRAP_CONFIG_KEY)
        except ClusterServiceUnavailableException:
            variables = {}
        bootstrap_bank = QuestionBank(
            questions=bootstrap_questions(),
            console=console,
            previous_answers=variables.get("bootstrap", {}),
        )
        preseed_content.extend(
            show_questions(bootstrap_bank, section="bootstrap")
        )

        # PostgreSQL questions
        try:
            variables = load_answers(client, POSTGRESQL_CONFIG_KEY)
        except ClusterServiceUnavailableException:
            variables = {}
        postgresql_config_bank = QuestionBank(
            questions=postgresql_questions(),
            console=console,
            previous_answers=variables,
        )
        preseed_content.extend(
            show_questions(postgresql_config_bank, section="postgres")
        )

        # HAProxy questions
        try:
            variables = load_answers(client, HAPROXY_CONFIG_KEY)
        except ClusterServiceUnavailableException:
            variables = {}
        qs = haproxy_questions()
        qs.update(tls_questions(HAPROXY_VALID_TLS_MODES))
        haproxy_config_bank = QuestionBank(
            questions=qs,
            console=console,
            previous_answers=variables,
        )
        preseed_content.extend(
            show_questions(haproxy_config_bank, section="haproxy")
        )

        # MAAS region questions
        try:
            variables = load_answers(client, MAASREGION_CONFIG_KEY)
        except ClusterServiceUnavailableException:
            variables = {}
        maas_region_config_bank = QuestionBank(
            questions=tls_questions(MAAS_REGION_VALID_TLS_MODES),
            console=console,
            previous_answers=variables,
        )
        preseed_content.extend(
            show_questions(maas_region_config_bank, section="maas-region")
        )

        preseed_content_final = "\n".join(preseed_content)
        return preseed_content_final
