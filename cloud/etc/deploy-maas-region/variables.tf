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

variable "arch" {
  description = "The system architecture of the cluster nodes"
  type        = string
  default     = "amd64"
}

variable "charm_maas_region_channel" {
  description = "Operator channel for MAAS Region Controller deployment"
  type        = string
  default     = "latest/edge"
}

variable "charm_maas_region_revision" {
  description = "Operator channel revision for MAAS Region Controller deployment"
  type        = number
  default     = null
}

variable "charm_maas_region_config" {
  description = "Operator config for MAAS Region Controller deployment"
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

variable "enable_haproxy" {
  description = "Whether to enable HAProxy integration"
  type        = bool
  default     = false
}

variable "tls_mode" {
  description = "TLS Mode for MAAS Region charm ('disabled', 'termination', or 'passthrough')"
  type        = string
  default     = "disabled"
}

variable "ssl_cert_content" {
  description = "SSL certificate for tls_mode=passthrough"
  type        = string
  default     = ""
}

variable "ssl_key_content" {
  description = "SSL private key for tls_mode=passthrough"
  type        = string
  default     = ""
}

variable "ssl_cacert_content" {
  description = "CA Cert chain for self-signed certificates, requires tls_mode=passthrough"
  type        = string
  default     = ""
}
