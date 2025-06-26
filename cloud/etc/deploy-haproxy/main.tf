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
  virtual_ip = var.virtual_ip != "" ? { virtual_ip = var.virtual_ip } : {}
  services   = var.haproxy_services_yaml != "" ? { services = var.haproxy_services_yaml } : {}
  ssl_cert   = var.ssl_cert_content != "" ? { ssl_cert = base64encode(var.ssl_cert_content) } : {}
  ssl_key    = var.ssl_key_content != "" ? { ssl_key = base64encode(var.ssl_key_content) } : {}
}

resource "juju_application" "haproxy" {
  name  = "haproxy"
  model = data.juju_model.machine_model.name
  units = length(var.machine_ids) # need to manage the number of units

  charm {
    name     = "haproxy"
    channel  = var.charm_haproxy_channel
    revision = var.charm_haproxy_revision
    base     = "ubuntu@24.04"
  }

  config = merge(
    local.services,
    local.ssl_cert,
    local.ssl_key,
    var.charm_haproxy_config,
  )

  constraints = join(" ", [
    "arch=${var.arch}",
  ])
}

resource "juju_application" "keepalived" {
  count = min(length(var.virtual_ip), 1)
  name  = "keepalived"
  model = data.juju_model.machine_model.name
  units = 0 # subordinate charm

  charm {
    name     = "keepalived"
    channel  = var.charm_keepalived_channel
    revision = var.charm_keepalived_revision
    base     = "ubuntu@24.04"
  }

  config = merge(
    { port = var.haproxy_port },
    local.virtual_ip,
    var.charm_keepalived_config,
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
