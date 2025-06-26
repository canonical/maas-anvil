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

MAAS_REGION_CHANNEL = "3.6/edge"
MAAS_AGENT_CHANNEL = "3.6/edge"
POSTGRESQL_CHANNEL = "16/beta"
S3_CHANNEL = "1/stable"
HAPROXY_CHANNEL = "latest/stable"
KEEPALIVED_CHANNEL = "latest/stable"

MACHINE_CHARMS = {
    "maas-region": MAAS_REGION_CHANNEL,
    "maas-agent": MAAS_AGENT_CHANNEL,
    "haproxy": HAPROXY_CHANNEL,
    "postgresql": POSTGRESQL_CHANNEL,
    "keepalived": KEEPALIVED_CHANNEL,
    "s3-integrator": S3_CHANNEL,
}
K8S_CHARMS: dict[str, str] = {}

MANIFEST_CHARM_VERSIONS: dict[str, str] = {}
MANIFEST_CHARM_VERSIONS |= K8S_CHARMS
MANIFEST_CHARM_VERSIONS |= MACHINE_CHARMS

TERRAFORM_DIR_NAMES = {
    "maas-region-plan": "deploy-maas-region",
    "maas-agent-plan": "deploy-maas-agent",
    "haproxy-plan": "deploy-haproxy",
    "postgresql-plan": "deploy-postgresql",
    "s3-plan": "deploy-s3",
}

DEPLOY_MAAS_REGION_TFVAR_MAP = {
    "charms": {
        "maas-region": {
            "channel": "charm_maas_region_channel",
            "revision": "charm_maas_region_revision",
            "config": "charm_maas_region_config",
        },
    }
}

DEPLOY_MAAS_AGENT_TFVAR_MAP = {
    "charms": {
        "maas-agent": {
            "channel": "charm_maas_agent_channel",
            "revision": "charm_maas_agent_revision",
            "config": "charm_maas_agent_config",
        }
    }
}

DEPLOY_HAPROXY_TFVAR_MAP = {
    "charms": {
        "haproxy": {
            "channel": "charm_haproxy_channel",
            "revision": "charm_haproxy_revision",
            "config": "charm_haproxy_config",
        },
        "keepalived": {
            "channel": "charm_keepalived_channel",
            "revision": "charm_keepalived_revision",
            "config": "charm_keepalived_config",
        },
    }
}

DEPLOY_POSTGRESQL_TFVAR_MAP = {
    "charms": {
        "postgresql": {
            "channel": "charm_postgresql_channel",
            "revision": "charm_postgresql_revision",
            "config": "charm_postgresql_config",
        },
    }
}

DEPLOY_S3_TFVAR_MAP = {
    "charms": {
        "s3-integrator": {
            "channel": "charm_s3_integrator_channel",
            "revision": "charm_s3_integrator_revision",
            "config": "charm_s3_integrator_config",
        }
    }
}

MANIFEST_ATTRIBUTES_TFVAR_MAP = {
    "maas-region-plan": DEPLOY_MAAS_REGION_TFVAR_MAP,
    "maas-agent-plan": DEPLOY_MAAS_AGENT_TFVAR_MAP,
    "haproxy-plan": DEPLOY_HAPROXY_TFVAR_MAP,
    "postgresql-plan": DEPLOY_POSTGRESQL_TFVAR_MAP,
    "s3-plan": DEPLOY_S3_TFVAR_MAP,
}
