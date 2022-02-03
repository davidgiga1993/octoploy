from __future__ import annotations

from typing import List, Optional, Dict

from octoploy.config.BaseConfig import BaseConfig
from octoploy.config.ConfigMap import ConfigMap
from octoploy.config.DeploymentActionConfig import DeploymentActionConfig
from octoploy.utils.DictUtils import DictUtils
from octoploy.utils.Errors import MissingVar


class AppConfig(BaseConfig):
    """
    Contains the configuration for the deployment of a single app
    """

    def __init__(self, config_root: str, path: Optional[str], external_vars: Dict[str, str] = None):
        super().__init__(path, external_vars)
        self._config_root = config_root

    def get_config_maps(self) -> List[ConfigMap]:
        """
        Returns additional config maps which should contain the content of a file
        """
        return [ConfigMap(data) for data in self.data.get('configmaps', [])]

    def enabled(self) -> bool:
        """
        True if this app is enabled
        """
        return self.data.get('enabled', False)

    def is_template(self) -> bool:
        """
        Indicates if this app is a template
        """
        return self.data.get('type', 'app') == 'template'

    def get_config_root(self) -> str:
        """
        Returns the path to the app config folder
        :return: Folder path
        """
        return self._config_root

    def get_for_each(self) -> List[AppConfig]:
        """
        Returns all instances of this app which should be created.
        :return: Instances, 1 by default
        :raise MissingVar: Gets raised if the data inside forEach is not complete
        """
        instances = []
        for instance_vars in self.data.get('forEach', []):
            assert isinstance(instance_vars, dict)
            dc_name = instance_vars.get('DC_NAME')
            if dc_name is None:
                raise MissingVar('DC_NAME not defined in forEach for app ' + self.get_dc_name())

            config = AppConfig(self._config_root, None, instance_vars)
            # Inherit all parameters
            config.data.update(self.data)
            # Update the DC_NAME
            DictUtils.set(config.data, 'dc.name', dc_name)
            instances.append(config)

        if len(instances) == 0:
            # No forEach defined, just create one instance
            instances.append(self)
        return instances

    def get_pre_template_refs(self) -> List[str]:
        """
        Returns the name of the templates that should be applied before processing own objects

        :return: Template names
        """
        return self.data.get('applyTemplates', [])

    def get_post_template_refs(self) -> List[str]:
        """
        Returns the name of the templates that should be applied after processing own objects

        :return: Template names
        """
        return self.data.get('postApplyTemplates', [])

    def get_reload_actions(self) -> List[DeploymentActionConfig]:
        """
        Returns all actions that should be executed after a configuration change of the app
        """
        return [DeploymentActionConfig(self, x) for x in self.data.get('on-config-change', [])]

    def get_dc_name(self) -> Optional[str]:
        """
        Returns the configured name of the deployment config
        :return: Name
        """
        return DictUtils.get(self.data, 'dc.name')

    def get_replacements(self) -> Dict[str, str]:
        """
        Returns all variables which are available for the yml files
        :return: Key, value map
        """
        items = super().get_replacements()
        dc_name = self.get_dc_name()
        if dc_name is not None:
            items.update({
                'DC_NAME': dc_name
            })
        return items
