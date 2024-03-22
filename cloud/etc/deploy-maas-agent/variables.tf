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

variable "charm_maas_agent_channel" {
  description = "Operator channel for MAAS Agent deployment"
  type        = string
  default     = "latest/edge"
}

variable "charm_maas_agent_revision" {
  description = "Operator channel revision for MAAS Agent deployment"
  type        = number
  default     = null
}

variable "charm_maas_agent_config" {
  description = "Operator config for MAAS Agent deployment"
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
