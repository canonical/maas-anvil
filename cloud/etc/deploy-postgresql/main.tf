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

locals {
  max_connections = var.max_connections == "default" ? {} : (
    var.max_connections == "dynamic" ? {
      experimental_max_connections = max(100, 10 + var.max_connections_per_region * var.maas_region_nodes)
      } : {
      experimental_max_connections = tonumber(var.max_connections)
    }
  )
}

resource "juju_application" "postgresql" {
  name  = "postgresql"
  model = data.juju_model.machine_model.name
  units = length(var.machine_ids) # need to manage the number of units

  charm {
    name     = "postgresql"
    channel  = var.charm_postgresql_channel
    revision = var.charm_postgresql_revision
    base     = "ubuntu@24.04"
  }

  config = merge(
    local.max_connections,
    # workaround for https://bugs.launchpad.net/maas/+bug/2097079
    { "plugin_audit_enable" : false },
    var.charm_postgresql_config
  )
}
