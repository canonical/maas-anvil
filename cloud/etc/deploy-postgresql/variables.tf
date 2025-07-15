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

variable "charm_postgresql_channel" {
  description = "Operator channel for PostgreSQL deployment"
  type        = string
  default     = "16/beta"
}

variable "charm_postgresql_revision" {
  description = "Operator channel revision for PostgreSQL deployment"
  type        = number
  default     = null
}

variable "charm_postgresql_config" {
  description = "Operator config for PostgreSQL deployment"
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

variable "max_connections" {
  description = "Maximum number of concurrent connections to allow to the database server"
  type        = string
  default     = "default"
}

variable "maas_region_nodes" {
  description = "Total number of MAAS region nodes"
  type        = number
  default     = 0
}

variable "max_connections_per_region" {
  description = "Maximum number of concurrent connections to allow to the database server per region"
  type        = number
  default     = 50
}

variable "charm_s3_integrator_channel" {
  description = "Operator channel for S3 Integrator deployment"
  type        = string
  default     = "2/edge"
}

variable "charm_s3_integrator_revision" {
  description = "Operator channel revision for S3 Integrator deployment"
  type        = number
  # default     = null
  # This version contains: https://github.com/canonical/object-storage-integrators/pull/36
  default = 165
}

variable "charm_s3_integrator_config" {
  description = "Operator config for S3 Integrator deployment"
  type        = map(string)
  default     = {}
}

variable "s3_enabled" {
  description = "Whether we should enable s3 integration"
  type        = bool
  default     = false
}

variable "access_key" {
  description = "Access key used to access the S3 backup bucket"
  type        = string
  default     = ""
}

variable "secret_key" {
  description = "Secret key used to access the S3 backup bucket"
  type        = string
  sensitive   = true
  default     = ""
}

variable "endpoint" {
  description = "Endpoint the S3 backup exists at. Leave empty to derive endpoint from region: `https://s3.{region}.amazonaws.com`"
  type        = string
  default     = ""
}

variable "bucket" {
  description = "Bucket name to store PostgreSQL backups in"
  type        = string
  default     = ""
}

variable "region" {
  description = "The AWS region the S3 bucket is in"
  type        = string
  default     = ""
}
