from __future__ import annotations

from abc import abstractmethod
from typing import Dict, Optional

from octoploy.k8s.BaseObj import BaseObj
from octoploy.utils.DictUtils import DictUtils


class NamedItem:
    def __init__(self, data):
        self.data = data

    @abstractmethod
    def get_name(self) -> str:
        pass


class ItemDescription:
    def __init__(self, data):
        self.data = data

    def get_annotation(self, key: str) -> Optional[str]:
        return self.data.get('metadata', {}).get('annotations', {}).get(key)


class PodData:
    def __init__(self):
        self.name = ''
        self.ready = False
        self.version = 0
        self.deployment_config = None
        """
        Name of the associated deployment config
        """

    def set_labels(self, labels):
        self.deployment_config = labels.get('deploymentconfig')


class DeploymentConfig(BaseObj):
    def __init__(self, data: BaseObj):
        super().__init__(data.data)

    def get_template(self) -> Optional[dict]:
        """
        Returns the template object
        """
        return DictUtils.get(self.data, 'spec.template')

    def get_template_spec(self) -> Optional[dict]:
        """
        Returns the template spec
        """
        return self.get_template().get('spec')

    def get_template_name(self) -> Optional[str]:
        """
        Returns the name of the template
        :return: Name or None if no name is defined
        """
        return DictUtils.get(self.get_template(), 'metadata.labels.name')

    def get_containers(self) -> Dict[str, DeploymentConfigContainer]:
        items = self.get_template_spec().get('containers', [])
        out = {}
        for data in items:
            container = DeploymentConfigContainer(data)
            out[container.get_name()] = container
        return out

    def get_volumes(self) -> Dict[str, DeploymentConfigVolume]:
        items = self.get_template_spec().get('volumes', [])
        out = {}
        for data in items:
            volume = DeploymentConfigVolume(data)
            out[volume.get_name()] = volume
        return out

    def add_container(self, item: DeploymentConfigContainer):
        self._add_to_list(self.get_template_spec(), 'containers', item.data)

    def add_volume(self, item: DeploymentConfigVolume):
        self._add_to_list(self.get_template_spec(), 'volumes', item.data)

    @staticmethod
    def _add_to_list(data, key: str, new_item: any):
        if key in data:
            data[key].append(new_item)
            return
        data[key] = [new_item]


class DeploymentConfigVolume(NamedItem):
    def get_name(self) -> str:
        return self.data['name']


class DeploymentConfigContainer(NamedItem):
    def get_name(self) -> str:
        return self.data['name']
