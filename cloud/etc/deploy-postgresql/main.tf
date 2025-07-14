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

  s3_config = merge(
    {
      "endpoint" = coalesce(var.endpoint, "https://s3.${var.region}.amazonaws.com")
      "bucket"   = var.bucket
      "path"     = "/postgresql"
      "region"   = var.region
    },
    var.charm_s3_integrator_config,
  )

  s3_enabled = var.s3_enabled ? 1 : 0
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

  constraints = join(" ", [
    "arch=${var.arch}",
  ])
}


resource "juju_secret" "s3_credentials" {
  count = local.s3_enabled

  model = data.juju_model.machine_model.name
  name  = "s3_credentials"

  value = {
    "access-key" = var.access_key
    "secret-key" = var.secret_key
  }
  info = "Credentials used to access S3"
}

resource "juju_application" "s3_integrator" {
  count = local.s3_enabled

  name  = "s3-integrator-postgresql"
  model = data.juju_model.machine_model.name

  # TODO: This one should go away when we move out of manual cloud
  placement = "0"

  charm {
    name     = "s3-integrator"
    channel  = var.charm_s3_integrator_channel
    revision = var.charm_s3_integrator_revision
    base     = "ubuntu@24.04"
  }

  config = merge(
    local.s3_config,
    { "credentials" = "secret:${juju_secret.s3_credentials[0].secret_id}" },
  )

  constraints = "arch=${var.arch}"
}

resource "juju_access_secret" "s3_credentials" {
  count = local.s3_enabled

  model        = data.juju_model.machine_model.name
  applications = [juju_application.s3_integrator[0].name]
  secret_id    = juju_secret.s3_credentials[0].secret_id
}

resource "juju_integration" "postgresql_s3_integration" {
  count = local.s3_enabled

  model = data.juju_model.machine_model.name

  application {
    name     = juju_application.s3_integrator[0].name
    endpoint = "s3-credentials"
  }

  application {
    name     = juju_application.postgresql.name
    endpoint = "s3-parameters"
  }
}
