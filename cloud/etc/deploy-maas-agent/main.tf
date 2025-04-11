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

terraform {

  required_providers {
    juju = {
      source  = "juju/juju"
      version = "= 0.15.1"
    }
  }

}

provider "juju" {}

data "juju_model" "machine_model" {
  name = var.machine_model
}

resource "juju_application" "maas-agent" {
  name  = "maas-agent"
  model = data.juju_model.machine_model.name
  units = length(var.machine_ids) # need to manage the number of units

  charm {
    name     = "maas-agent"
    channel  = var.charm_maas_agent_channel
    revision = var.charm_maas_agent_revision
    base     = "ubuntu@24.04"
  }

  config = var.charm_maas_agent_config
}

resource "juju_integration" "maas-agent-region" {
  model = data.juju_model.machine_model.name

  application {
    name     = juju_application.maas-agent.name
    endpoint = "maas-region"
  }

  application {
    name     = "maas-region"
    endpoint = "maas-region"
  }
}
