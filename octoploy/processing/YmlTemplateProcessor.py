from __future__ import annotations

import re
from typing import Optional, Dict, List, Set
from typing import TYPE_CHECKING

from octoploy.k8s.BaseObj import BaseObj
from octoploy.processing.TreeWalker import TreeWalker, TreeProcessor
from octoploy.utils.Log import Log

if TYPE_CHECKING:
    from octoploy.config.BaseConfig import BaseConfig
from octoploy.utils.Errors import MissingParam


class YmlTemplateProcessor(Log, TreeProcessor):
    """
    Processes yml files by replacing any string placeholders.
    """

    VAR_PATTERN = re.compile(r'\${(.+?)}')
    KEY_FIELD_MERGE: str = '_merge'

    _replacements: Dict[str, any] = {}

    def __init__(self, config: BaseConfig):
        super().__init__()
        self._missing_vars = []  # type: List[str]
        """
        List of all variables which have not been replace because
        there was no value defined for them
        """
        self._config = config  # type: BaseConfig
        self._parent = None  # type: Optional[YmlTemplateProcessor]
        self._child = None  # type: Optional[YmlTemplateProcessor]

        self._replacements = {}

    def parent(self, template_processor: YmlTemplateProcessor):
        """
        Inherits all replacements from the given processor.
        If the same value is defined in this and the parent, the definition of this processor will override
        the parent definition

        :param template_processor: Child processor
        """
        if self._parent is not None:
            raise ValueError('Parent processor already defined')
        self._parent = template_processor

    def child(self, template_processor: YmlTemplateProcessor):
        """
        Inherits all replacements from the given processor.
        If the same value is defined in this and the child, the definition of the child processor will override
        this definition

        :param template_processor: Child processor
        """
        if self._child is not None:
            raise ValueError('Child processor already defined')
        self._child = template_processor

    def process(self, k8s_object: BaseObj):
        """
        Processes the app data

        :param k8s_object: Data of the app, the data will be modified in place
        :raise MissingParam: Gets raised if at least one parameter is not defined
        """
        self._load_replacements()

        # Now replace any placeholders in the actual data tree
        walker = TreeWalker(self)
        walker.walk(k8s_object.data)
        k8s_object.refresh()

        # Check if any of the missing vars are declared as "params"
        # (aka are required)
        if len(self._missing_vars) > 0:
            missing_params = []
            params = self._get_params()
            for missing in self._missing_vars:
                if missing not in params:
                    continue
                missing_params.append(missing)
            if len(missing_params) > 0:
                raise MissingParam('The following params are not defined: ' + str(missing_params))
            self.log.warning('The following vars are not defined: ' + str(self._missing_vars))

    def _get_params(self) -> Set[str]:
        """
        Returns all defined params
        :return: Param names
        """
        params = set()
        if self._parent is not None:
            params.update(self._parent._get_params())
        params.update(self._config.get_params())
        if self._child is not None:
            params.update(self._child._get_params())
        return params

    def process_object(self, data: Dict[str, any], parent: Dict[str, any], key: str) -> Optional[Dict[str, any]]:
        if key == self.KEY_FIELD_MERGE:
            # Remove the item from the parent
            # and merge it into the parent itself
            del parent[key]
            TreeWalker(self).walk(data)
            parent.update(data)
            return None
        return data

    def process_str(self, value: str, parent: Dict[str, any], key: str) -> any:
        if key == self.KEY_FIELD_MERGE:
            # Remove the item from the parent
            # and merge it into the parent itself
            del parent[key]
            new_value = self._replace(value)
            if isinstance(new_value, str):
                raise ValueError(f'No replacement found for {new_value}')
            parent.update(new_value)
            return None

        return self._replace(value)

    def _replace(self, item: str) -> any:
        """
        Replaces the given variable with the actual value
        :param item: Variable in the format "${KEY}"
        :return: Value or item if no replacement was found
        """
        for variable, value in self._replacements.items():
            if item == '${' + variable + '}':
                # Item only contains a tag, simple replace (non textual)
                return value
            # The variable tag is surrounded by other str or other tags
            item = item.replace('${' + variable + '}', str(value))

        # Search for any missing variables
        if isinstance(item, str):
            self._missing_vars.extend(self.VAR_PATTERN.findall(item))
        return item

    def _load_replacements(self):
        """
        Loads all available replacements
        """
        self._replacements = self._get_replacements()
        self._resolve_refs(self._replacements)

    def _get_replacements(self) -> Dict[str, any]:
        """
        Returns all replacements handled by this processor, including all parent variables
        :return: Replacements
        """
        replacements = {}
        if self._parent is not None:
            replacements.update(self._parent._get_replacements())
        replacements.update(self._config.get_replacements())
        if self._child is not None:
            replacements.update(self._child._get_replacements())
        return replacements

    def _resolve_refs(self, data: Dict[str, any]):
        """
        Resolves any references in the given replacements (in place)
        :param data: Replacements
        """

        found_var = True
        while found_var:
            found_var = False
            for key, value in data.items():
                if isinstance(value, dict):
                    # A replacement might be an object
                    # So we need to walk through every item and see if there is something to replace
                    self._resolve_refs(value)
                    continue
                if not isinstance(value, str):
                    continue

                # The replacement value might refer to another variable
                for variable_name in self.VAR_PATTERN.findall(value):
                    new_value = data.get(variable_name, self._replacements.get(variable_name))
                    if new_value is None:
                        self.log.warning('Missing referenced variable: ' + variable_name)
                        continue
                    if value == '${' + variable_name + '}':
                        # Replace the entire value since the replacement value only consists of the ${} tag
                        data[key] = new_value
                        found_var = True
                        continue

                    data[key] = value.replace('${' + variable_name + '}', str(new_value))
                    found_var = True
