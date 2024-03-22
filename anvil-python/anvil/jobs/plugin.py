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

import importlib
import logging
from pathlib import Path
from typing import Any, Dict

from sunbeam.jobs.deployment import Deployment
from sunbeam.jobs.plugin import (
    PLUGIN_YAML,
    PluginManager as SunbeamPluginManager,
)
import yaml

LOG = logging.getLogger(__name__)


class PluginManager(SunbeamPluginManager):
    @classmethod
    def get_core_plugins_path(cls) -> Path:
        """Returns the path where the core plugins are defined."""
        return Path(__file__).parent.parent / "plugins"

    @classmethod
    def get_plugins_map(
        cls,
        plugin_file: Path,
        raise_exception: bool = False,
    ) -> Dict[str, type]:
        """Return dict of {plugin name: plugin class} from plugin yaml.

        :param plugin_file: Plugin yaml file
        :param raise_exception: If set to true, raises an exception in case
                                plugin class is not loaded. By default, ignores
                                by logging the error message.

        :returns: Dict of plugin classes
        :raises: ModuleNotFoundError or AttributeError
        """
        plugins_yaml = {}
        with plugin_file.open() as file:
            plugins_yaml = yaml.safe_load(file)

        plugins = plugins_yaml.get("anvil-plugins", {}).get("plugins", [])
        plugin_classes = {}

        for plugin in plugins:
            module = None
            plugin_class = plugin.get("path")
            if plugin_class is None:
                continue
            module_class_ = plugin_class.rsplit(".", 1)
            try:
                module = importlib.import_module(module_class_[0])
                plugin_class = getattr(module, module_class_[1])
                plugin_classes[plugin["name"]] = plugin_class
            # Catching Exception instead of specific errors as plugins
            # can raise any exception based on implementation.
            except Exception as e:
                # Exceptions observed so far
                # ModuleNotFoundError, AttributeError, NameError
                LOG.debug(str(e))
                LOG.warning(f"Ignored loading plugin: {plugin_class}")
                if raise_exception:
                    raise e

                continue

        LOG.debug(f"Plugin classes: {plugin_classes}")
        return plugin_classes

    @classmethod
    def get_plugins(
        cls, deployment: Deployment, repos: list[Any] | None = []
    ) -> dict[Any, Any]:
        """Returns list of plugin name and description.

        Get all plugins information for each repo specified in repos.
        If repos is None or empty list, get plugins for all the repos
        including the internal plugins in snap-openstack repo. Repo name
        core is reserved for internal plugins in snap-openstack repo.

        :param deployment: Deployment instance.
        :param repos: List of repos
        :returns: Dictionary of repo with plugin name and description

        Sample output:
        {
            "core": {
                [
                    ("pro", "Ubuntu pro management plugin"),
                    ("repo", "External plugin repo management"
                ]
            }
        }
        """
        if not repos:
            repos.append("core")  # type: ignore[union-attr]
            repos.extend(cls.get_all_external_repos(deployment.get_client()))  # type: ignore[union-attr]

        plugins: dict[Any, Any] = {}
        for repo in repos:  # type: ignore[union-attr]
            if repo == "core":
                plugin_file = cls.get_core_plugins_path() / PLUGIN_YAML
            else:
                plugin_file = (
                    cls.get_external_plugins_base_path() / repo / PLUGIN_YAML
                )

            plugins_yaml = {}
            with plugin_file.open() as file:
                plugins_yaml = yaml.safe_load(file)

            plugins_list = plugins_yaml.get("anvil-plugins", {}).get(
                "plugins", {}
            )
            plugins[repo] = []
            plugins[repo].extend(
                [
                    (plugin.get("name"), plugin.get("description"))
                    for plugin in plugins_list
                ]
            )

        return plugins
