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

import logging
import sys

import click
from rich.status import Status
from sunbeam.clusterd.client import Client
from sunbeam.commands.juju import JujuStepHelper
from sunbeam.commands.terraform import TerraformException
from sunbeam.jobs.common import (
    BaseStep,
    Result,
    ResultType,
    update_status_background,
)
from sunbeam.jobs.juju import (
    JujuHelper,
    JujuWaitException,
    TimeoutException,
    run_sync,
)
from sunbeam.jobs.manifest import Manifest
from sunbeam.plugins.interface.v1.base import PluginError

LOG = logging.getLogger(__name__)
LOCAL_ACCESS = "local"
REMOTE_ACCESS = "remote"


class CatchGroup(click.Group):
    """Catch exceptions and print them to stderr."""

    def __call__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        try:
            return self.main(*args, **kwargs)
        except PluginError as e:
            LOG.debug(e, exc_info=True)
            LOG.error("Error: %s", e)
            sys.exit(1)
        except Exception as e:
            LOG.debug(e, exc_info=True)
            message = (
                "An unexpected error has occurred."
                " Please run 'maas-anvil inspect' to generate an inspection report."
            )
            LOG.warn(message)
            LOG.error("Error: %s", e)
            sys.exit(1)


# We reimplement from sunbeam to avoid openstack dependencies
class UpgradeCharm(BaseStep, JujuStepHelper):
    def __init__(
        self,
        name: str,
        description: str,
        client: Client,
        jhelper: JujuHelper,
        manifest: Manifest,
        model: str,
        charms: list[str],
        tfplan: str,
        config: str,
        timeout: int,
    ):
        super().__init__(name, description)
        self.client = client
        self.jhelper = jhelper
        self.manifest = manifest
        self.model = model
        self.charms = charms
        self.tfplan = tfplan
        self.config = config
        self.timeout = timeout

    def run(self, status: Status | None = None) -> Result:
        """Run control plane and machine charm upgrade."""
        apps = self.get_apps_filter_by_charms(self.model, self.charms)
        result = self.upgrade_applications(
            apps,
            self.charms,
            self.model,
            self.tfplan,
            self.config,
            self.timeout,
            status,
        )
        return result

    def upgrade_applications(
        self,
        apps: list[str],
        charms: list[str],
        model: str,
        tfplan: str,
        config: str,
        timeout: int,
        status: Status | None = None,
    ) -> Result:
        expected_wls = ["active", "blocked", "unknown"]
        LOG.debug(
            f"Upgrading applications using terraform plan {tfplan}: {apps}"
        )
        try:
            self.manifest.update_partial_tfvars_and_apply_tf(
                self.client, charms, tfplan, config
            )
        except TerraformException as e:
            LOG.exception("Error upgrading cloud")
            return Result(ResultType.FAILED, str(e))

        task = run_sync(update_status_background(self, apps, status))
        try:
            run_sync(
                self.jhelper.wait_until_desired_status(
                    model,
                    apps,
                    expected_wls,
                    timeout=timeout,
                )
            )
        except (JujuWaitException, TimeoutException) as e:
            LOG.debug(str(e))
            return Result(ResultType.FAILED, str(e))
        finally:
            if not task.done():
                task.cancel()

        return Result(ResultType.COMPLETED)
