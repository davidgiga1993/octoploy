from __future__ import annotations

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

    KEY_FIELD_MERGE: str = '_merge'

    _config: BaseConfig
    _replacements: Dict[str, any]
    _parents: List[YmlTemplateProcessor]
    _child: Optional[YmlTemplateProcessor]

    _missing_vars: List[str]
    """
    List of all variables which have not been replace because
    there was no value defined for them
    """

    def __init__(self, config: BaseConfig):
        super().__init__()
        self._missing_vars = []

        self._config = config
        self._parents = []
        self._child = None
        self._replacements = {}

    def parents(self, template_processor: List[YmlTemplateProcessor]):
        """
        Inherits all replacements from the given processor.
        If the same value is defined in this and the parent, the definition of this processor will override
        the parent definition

        :param template_processor: Child processor
        """
        if len(self._parents) > 0:
            raise ValueError('Parent processors already defined')
        self._parents = template_processor

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
        for parent in self._parents:
            params.update(parent._get_params())
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
        :param item: Variable in the format "${KEY}" "$$" will be escaped to "$"
        :return: Value or item if no replacement was found
        """
        new_item = ''
        var_name_buffer = ''
        mode = 0
        for char in item:
            if mode == 0:  # Search for tag start $
                if char == '$':
                    mode = 1
                    continue
                new_item += char
                continue

            if mode == 1:  # After $
                if char == '$':
                    # Escaped $
                    new_item += '$'
                    mode = 0
                    continue

                if char == '{':
                    mode = 2
                    var_name_buffer = ''
                    continue

                # Not a variable tag, just add the $ and the current char
                new_item += '$' + char
                mode = 0
                continue

            if mode == 2:  # After ${, search for end }
                if char == '}':
                    # End of variable tag found
                    mode = 0
                    new_val = self._replacements.get(var_name_buffer)
                    if new_val is None:
                        self._missing_vars.append(var_name_buffer)
                        new_item += '${' + var_name_buffer + '}'
                        continue

                    # The new_val can be an "object" as well,
                    # but we can only replace it if the given item
                    # only refers to this variable and is not a combination of strings
                    if item == '${' + var_name_buffer + '}':
                        return new_val

                    if not isinstance(new_val, str):
                        raise ValueError(f'Invalid replacement for {var_name_buffer}: Expected string, got {new_val}.\n'
                                         f'Non string replacements are only possible for single variable references.')
                    new_item += new_val
                    continue
                var_name_buffer += char
                continue

        if mode == 1:
            # Ended with a $
            new_item += '$'
        if mode == 2:
            # Ended with a ${, so we need to add the buffer
            new_item += '${' + var_name_buffer

        return new_item

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
        for parent in self._parents:
            replacements.update(parent._get_replacements())
        replacements.update(self._config.get_replacements())
        if self._child is not None:
            replacements.update(self._child._get_replacements())
        return replacements

    def _resolve_refs(self, data: Dict[str, any]):
        """
        Resolves any references in the given replacements (in place)
        :param data: Replacements
        """
        found_var_to_replace = True
        while found_var_to_replace:
            found_var_to_replace = False
            for key, value in data.items():
                if isinstance(value, dict):
                    # A replacement might be an object
                    # So we need to walk through every item and see if there is something to replace
                    self._resolve_refs(value)
                    continue
                if not isinstance(value, str):
                    continue

                # The replacement value might refer to another variable
                new_val = self._replace(value)
                if new_val != value:
                    data[key] = new_val
                    found_var_to_replace = True
                    continue
