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

provider "juju" {
  alias = "haproxy"
}

data "juju_model" "machine_model" {
  name = var.machine_model
}

resource "juju_application" "keepalived" {
  name  = "keepalived"
  model = data.juju_model.machine_model.name
  units = 1

  charm {
    name     = "keepalived"
    channel  = var.charm_keepalived_channel
    revision = var.charm_keepalived_revision
    base     = "ubuntu@22.04"
  }

  config = var.charm_keepalived_config
}

resource "juju_relation" "haproxy_keepalived" {
  provider = juju.haproxy
  requirer = juju_application.keepalived.name
}

resource "juju_config" "keepalived" {
  # do nothing if the vip is not given
  count       = var.virtual_ip != "" ? 1 : 0
  application = juju_application.keepalived.name
  model       = data.juju_model.machine_model.name

  config = {
    virtual_ip = var.virtual_ip
  }
}