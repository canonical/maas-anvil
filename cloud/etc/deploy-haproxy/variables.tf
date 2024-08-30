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

variable "charm_haproxy_channel" {
  description = "Operator channel for HAProxy deployment"
  type        = string
  default     = "14/stable"
}

variable "charm_haproxy_revision" {
  description = "Operator channel revision for HAProxy deployment"
  type        = number
  default     = null
}

variable "charm_haproxy_config" {
  description = "Operator config for HAProxy deployment"
  type        = map(string)
  default     = {}
}

variable "machine_ids" {
  description = "List of machine ids to include"
  type        = list(string)
  default     = []
}

variable "machine_model" {
  description = "Model to deploy to"
  type        = string
}

variable "charm_keepalived_channel" {
  description = "Operator channel for Keepalived"
  type        = string
  default     = "latest/stable"
}

variable "charm_keepalived_revision" {
  description = "Operator channel revision for Keepalived"
  type        = number
  default     = null
}

variable "virtual_ip" {
  description = "Virtual IP Address for Keepalived"
  type        = string
  default     = ""
}

variable "haproxy_services_yaml" {
  description = "yaml-formatted services definition for HAProxy charm"
  type        = string
  default     = ""
}

variable "ssl_cert_content" {
  description = "base64 encoded SSL Certificate content for HAProxy charm"
  type        = string
  default     = ""
}

variable "ssl_key_content" {
  description = "base64 encoded SSL Key content for HAProxy charm"
  type        = string
  default     = ""
}

variable "haproxy_port" {
  description = "The port that HAProxy listens on"
  type        = string
  default     = 80
}

variable "charm_keepalived_config" {
  description = "Operator config for Keepalived deployment"
  type        = map(string)
  default     = {}
}
