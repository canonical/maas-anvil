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
  s3_config = merge(
    {
      "endpoint" = "https://s3.${var.aws_region}.amazonaws.com"
      "bucket"   = var.aws_bucket
      "path"     = "/postgresql"
      "region"   = var.aws_region
    },
    var.charm_s3_integrator_config,
  )
  access_key = var.aws_access_key
  secret_key = var.aws_secret_key

  s3_enabled = 1 #var.s3_enabled ? 1 : 0
}

resource "juju_application" "s3_integrator" {
  count = local.s3_enabled
  name  = "s3-integrator"
  model = data.juju_model.machine_model.name

  charm {
    name    = "s3-integrator"
    channel = var.charm_s3_integrator_channel
  }

  config = local.s3_config

  constraints = "arch=${var.arch}"
}

resource "null_resource" "sync_s3_creds" {
  count = local.s3_enabled

  provisioner "local-exec" {
    command = <<-EOT
        juju run s3-integrator/leader sync-s3-credentials \
            access-key="$access" \
            secret-key="$secret"
    EOT
    environment = {
      access = local.access_key
      secret = local.secret_key
    }
  }

  depends_on = [
    juju_application.s3_integrator[0]
  ]
}

resource "juju_integration" "postgresql_s3_integration" {
  count = local.s3_enabled
  model = data.juju_model.machine_model.name

  application {
    name     = "s3-integrator"
    endpoint = "s3-credentials"
  }

  application {
    name     = "postgresql"
    endpoint = "s3-parameters"
  }

  depends_on = [
    null_resource.sync_s3_creds[0],
  ]
}
