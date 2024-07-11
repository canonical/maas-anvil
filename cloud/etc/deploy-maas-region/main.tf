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

resource "juju_application" "maas-region" {
  name  = "maas-region"
  model = data.juju_model.machine_model.name
  units = length(var.machine_ids) # need to manage the number of units

  charm {
    name     = "maas-region"
    channel  = var.charm_maas_region_channel
    revision = var.charm_maas_region_revision
    base     = "ubuntu@22.04"
  }

  config = var.charm_maas_region_config
}

resource "juju_application" "pgbouncer" {
  name  = "pgbouncer"
  model = data.juju_model.machine_model.name
  units = 0 # it is a subordinate charm

  charm {
    name     = "pgbouncer"
    channel  = var.charm_pgbouncer_channel
    revision = var.charm_pgbouncer_revision
    base     = "ubuntu@22.04"
  }

  config = merge({
    pool_mode          = "session"
    max_db_connections = var.max_connections_per_region
  }, var.charm_pgbouncer_config)
}

resource "juju_integration" "postgresql-pgbouncer" {
  model = data.juju_model.machine_model.name

  application {
    name     = "postgresql"
    endpoint = "database"
  }

  application {
    name     = juju_application.pgbouncer.name
    endpoint = "backend-database"
  }
}

resource "juju_integration" "maas-region-pgbouncer" {
  model = data.juju_model.machine_model.name

  application {
    name     = juju_application.maas-region.name
    endpoint = "maas-db"
  }

  application {
    name     = juju_application.pgbouncer.name
    endpoint = "database"
  }
}

resource "juju_integration" "maas-region-haproxy" {
  count = var.enable_haproxy ? 1 : 0
  model = data.juju_model.machine_model.name

  application {
    name     = juju_application.maas-region.name
    endpoint = "api"
  }

  application {
    name     = "haproxy"
    endpoint = "reverseproxy"
  }
}
