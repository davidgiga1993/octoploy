from typing import Dict

from octoploy.oc.Model import DeploymentConfig, NamedItem
from octoploy.utils.DictUtils import DictUtils
from octoploy.utils.Log import Log


class OcObjectMerge(Log):
    """
    Merges openshift objects
    """
    NAME_PATH = 'metadata.name'

    def __init__(self):
        super().__init__()
        self._existing_dc = None  # type: DeploymentConfig
        self._new_dc = None  # type: DeploymentConfig

    def merge(self, existing, to_add) -> bool:
        """
        Merges the given openshift object into one.
        :param existing: Existing where the data should be added to
        :param to_add: New data
        :return: True if the data has been merged, false otherwise
        """
        expected_type = existing['kind'].lower()
        type_str = to_add['kind'].lower()
        if expected_type != type_str:
            return False

        expected_name = DictUtils.get(existing, self.NAME_PATH)
        name = DictUtils.get(to_add, self.NAME_PATH)
        if name is not None and expected_name is not None and expected_name != name:
            return False

        if expected_type == 'DeploymentConfig'.lower():
            self._merge_dc(DeploymentConfig(existing), DeploymentConfig(to_add))
            return True

        self.log.warning('Don\'t know how to merge ' + expected_type)

    def _merge_dc(self, existing: DeploymentConfig, to_add: DeploymentConfig):
        """
        Merges the given deployment configs if their name match
        :param existing: Deployment config where the data should be added
        :param to_add: New data
        """
        self._existing_dc = existing
        self._new_dc = to_add
        to_add_template_name = to_add.get_template_name()
        existing_template_name = existing.get_template_name()
        # If the name of a template is not defined it will be merged regardless of the name of the existing template
        if to_add_template_name is not None and existing_template_name is not None \
                and existing.get_template_name() != to_add_template_name:
            return

        # Containers and volumes need special treatment
        self._merge_object(existing.data, to_add.data, {
            'spec': {'template': {'spec': {
                'containers': True,
                'volumes': True
            }}}})

        self._merge_named_item(existing.get_containers(), to_add.get_containers(), existing.add_container)
        self._merge_named_item(existing.get_volumes(), to_add.get_volumes(), existing.add_volume)

    def _merge_object(self, existing: dict, new_data: dict, ignore_keys: Dict[str, any]):
        """
        Merges the given dict
        :param existing: Dict where the data should be merged to
        :param new_data: New data
        """
        for key, item in new_data.items():
            if ignore_keys.get(key, False) is True:
                continue
            if key not in existing:
                existing[key] = item
                continue
            parent_item = existing[key]
            if isinstance(item, list):
                parent_item.extend(item)
                continue
            if isinstance(item, dict):
                self._merge_object(parent_item, item, ignore_keys.get(key, {}))
                continue
            if item == parent_item:
                continue

            existing[key] = item
            self.log.warning(f'Value conflict: {item} (from {self._new_dc.get_template_name()}) replaces ' + \
                             f'{parent_item} (from {self._existing_dc.get_template_name()})')

    def _merge_named_item(self, existing_items: Dict[str, NamedItem], new_item: Dict[str, NamedItem], add_func_call):
        """
        Merges a named item object
        :param existing_items: Parent items, mapped to their name
        :param new_item: New items, mapped to their name
        :param add_func_call: Function call for adding an item to the parent
        """
        for name, new_container in new_item.items():
            if name in existing_items:
                # Merge data
                self._merge_object(existing_items[name].data, new_container.data, {})
                continue

            # Additional item
            add_func_call(new_container)
