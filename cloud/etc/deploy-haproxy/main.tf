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
      version = "= 0.11.0"
    }
  }

}

provider "juju" {}

data "juju_model" "machine_model" {
  name = var.machine_model
}

resource "juju_application" "haproxy" {
  name  = "haproxy"
  model = data.juju_model.machine_model.name
  units = length(var.machine_ids) # need to manage the number of units

  charm {
    name     = "haproxy"
    channel  = var.charm_haproxy_channel
    revision = var.charm_haproxy_revision
    base     = "ubuntu@22.04"
  }

  config = var.charm_haproxy_config
}

resource "juju_application" "keepalived" {
  count = min(length(var.virtual_ip), 1)
  name  = "keepalived"
  model = data.juju_model.machine_model.name

  charm {
    name     = "keepalived"
    channel  = var.charm_keepalived_channel
    revision = var.charm_keepalived_revision
    base     = "ubuntu@22.04"
  }

  config = merge(
    var.charm_keepalived_config,
    {
      "virtual_ip": var.virtual_ip,
    }
  )
}

resource "juju_integration" "maas-region-haproxy" {
  count = min(length(var.virtual_ip), 1)
  model = data.juju_model.machine_model.name

  application {
    name     = juju_application.haproxy.name
    endpoint = "juju-info"
  }

  application {
    name     = juju_application.keepalived[0].name
    endpoint = "juju-info"
  }
}
