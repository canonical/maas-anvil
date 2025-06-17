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

  constraints = join(" ", [
    "arch=${var.arch}",
  ])
}

resource "juju_application" "s3_integrator" {
  name      = "s3-integrator"
  model     = data.juju_model.machine_model.name
  units     = 3
  placement = ["0", "1", "2"]

  charm {
    name    = "s3-integrator"
    channel = var.charm_s3_integrator_channel
  }

  config = merge(
    {
      "endpoint" = "https://s3.${var.aws_region}.amazonaws.com"
      "bucket"   = var.aws_bucket
      "path"     = "/postgresql"
      "region"   = var.aws_region
    },
    var.charm_s3_integrator_config,
  )

  constraints = "arch=${var.arch}"
}

resource "terraform_data" "juju_wait_for_s3_postgres" {
  input = {
    model = juju_application.s3_integrator.model
  }

  provisioner "local-exec" {
    command = <<-EOT
      juju wait-for model "$MODEL" --timeout 3600s \
        --query='
            all(
                filter(
                    units,
                    unit => startsWith(unit.application.name, "s3-integrator") || startsWith(unit.application.name, "postgresql")
                ),
            unit => unit.workload-status == "active"
        )'
    EOT
    environment = {
      MODEL = self.input.model
    }
  }
}

resource "terraform_data" "sync_credentials" {
  input = {
    model = terraform_data.juju_wait_for_s3_postgres.model
  }

  provisioner "local-exec" {
    command = <<-EOT
        juju run s3-integrator/leader sync-s3-credentials \
            access-key="${AWS_ACCESS_KEY}" \
            secret-key="${AWS_SECRET_KEY}"
    EOT
    environment = {
      AWS_ACCESS_KEY = var.aws_access_key
      AWS_SECRET_KEY = var.aws_secret_key
    }
  }
}

resource "juju_integration" "postgresql_s3_integration" {
  model = terraform_data.sync_credentials.model

  application {
    name     = "s3-integrator"
    endpoint = "s3"
  }

  application {
    name     = "postgresql"
    endpoint = "database"
  }
}
