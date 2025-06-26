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

variable "machine_model" {
  description = "Model to deploy to"
  type        = string
}

variable "machine_ids" {
  description = "List of machine ids to include"
  type        = list(string)
  default     = []
}

variable "charm_s3_integrator_channel" {
  description = "Operator channel for S3 Integrator deployment"
  type        = string
  default     = "1/stable"
}

variable "charm_s3_integrator_revision" {
  description = "Operator channel revision for S3 Integrator deployment"
  type        = number
  default     = null
}

variable "charm_s3_integrator_config" {
  description = "Operator config for S3 Integrator deployment"
  type        = map(string)
  default     = {}
}

variable "machine_ids" {
  description = "List of machine ids to include"
  type        = list(string)
  default     = []
}
variable "machine_ids" {
  description = "List of machine ids to include"
  type        = list(string)
  default     = []
}
variable "machine_ids" {
  description = "List of machine ids to include"
  type        = list(string)
  default     = []
}
variable "machine_ids" {
  description = "List of machine ids to include"
  type        = list(string)
  default     = []
}
variable "machine_ids" {
  description = "List of machine ids to include"
  type        = list(string)
  default     = []
}
variable "machine_ids" {
  description = "List of machine ids to include"
  type        = list(string)
  default     = []
}
variable "s3_enabled" {
    description = "Whether we should enable s3 integration"
    type        = bool
    default     = true
}

variable "aws_access_key" {
    description = "Access key used to access the S3 backup bucket"
    type        = string
    default     = "admin"
}

variable "aws_secret_key" {
    description = "Secret key used to access the S3 backup bucket"
    type        = string
    sensitive   = true
    default     = "password"
}

variable "aws_bucket" {
    description = "Bucket name to store MAAS backups in"
    type        = string
    default     = "anvil"
}

variable "aws_region" {
    description = "The AWS region the S3 bucket is in"
    type        = string
    default     = "minio"
}
