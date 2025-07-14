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
  tls_mode           = var.tls_mode != "" ? { tls_mode = var.tls_mode } : {}
  ssl_cert_content   = var.ssl_cert_content != "" ? { ssl_cert_content = var.ssl_cert_content } : {}
  ssl_key_content    = var.ssl_key_content != "" ? { ssl_key_content = var.ssl_key_content } : {}
  ssl_cacert_content = var.ssl_cacert_content != "" ? { ssl_cacert_content = var.ssl_cacert_content } : {}

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

resource "juju_application" "maas-region" {
  name  = "maas-region"
  model = data.juju_model.machine_model.name
  units = length(var.machine_ids) # need to manage the number of units

  charm {
    name     = "maas-region"
    channel  = var.charm_maas_region_channel
    revision = var.charm_maas_region_revision
    base     = "ubuntu@24.04"
  }

  config = merge(
    local.tls_mode,
    local.ssl_cert_content,
    local.ssl_key_content,
    local.ssl_cacert_content,
    var.charm_maas_region_config,
  )

  constraints = join(" ", [
    "arch=${var.arch}",
  ])
}

resource "juju_integration" "maas-region-postgresql" {
  model = data.juju_model.machine_model.name

  application {
    name     = juju_application.maas-region.name
    endpoint = "maas-db"
  }

  application {
    name     = "postgresql"
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

# Configure S3 if desired
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

  name  = "s3-integrator"
  model = data.juju_model.machine_model.name

  # TODO: This one should go away when we move out of manual cloud
  placement = "0"

  charm {
    name     = "s3-integrator-region"
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

resource "juju_integration" "maas_region_s3_integration" {
  count = local.s3_enabled

  model = data.juju_model.machine_model.name

  application {
    name     = juju_application.s3_integrator[0].name
    endpoint = "s3-credentials"
  }

  application {
    name     = juju_application.maas-region.name
    endpoint = "s3-parameters"
  }
}
