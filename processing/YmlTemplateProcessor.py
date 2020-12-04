from __future__ import annotations

import re
from typing import Optional, Dict, List, Set
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config.BaseConfig import BaseConfig
from utils.Errors import MissingParam


class YmlTemplateProcessor:
    """
    Processes yml files by replacing any string placeholders.
    """

    VAR_PATTERN = re.compile(r'\${(.+)}')

    def __init__(self, config: BaseConfig):
        self._missing_vars = []  # type: List[str]
        """
        List of all variables which have not been replace because
        there was no value defined for them
        """
        self._config = config  # type: BaseConfig
        self._parent = None  # type: Optional[YmlTemplateProcessor]
        self._child = None  # type: Optional[YmlTemplateProcessor]

    def process(self, data: dict):
        """
        Processes the app data

        :param data: Data of the app, the data will be modified in place
        :raise MissingParam: Gets raised if at least one parameter is not defined
        """
        replacements = self._get_replacements()
        # Replace any variables
        depth = 0
        found_var = True
        while depth < 10 and found_var:  # Lazily assume there are only 10 levels of chained reference
            found_var = False
            for key, value in replacements.items():
                if not isinstance(value, str):
                    continue
                for variable_name in self.VAR_PATTERN.findall(value):
                    new_value = replacements.get(variable_name)
                    if new_value is None:
                        print('Warn: Missing referenced variable: ' + variable_name)
                        continue
                    replacements[key] = value.replace('${' + variable_name + '}', str(new_value))
                    found_var = True

        self._walk_dict(replacements, data)

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
            print('Warn: The following vars are not defined: ' + str(self._missing_vars))

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

    def _get_replacements(self) -> Dict[str, str]:
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

    def _walk_dict(self, replacements: Dict[str, str], data: dict):
        """
        Walks through all items in the dict and replaces any known variables
        :param replacements: Data which should be used as a replacement
        :param data: Data which should be walked
        """
        for key, obj in data.items():
            data[key] = self._walk_item(replacements, obj)
        return data

    def _walk_item(self, replacements, obj):
        if isinstance(obj, list):
            for idx, item in enumerate(obj):
                obj[idx] = self._walk_item(replacements, item)
            return obj

        if isinstance(obj, str):
            return self._replace(obj, replacements)

        if isinstance(obj, dict):
            return self._walk_dict(replacements, obj)
        return obj

    def _replace(self, item: str, replacements):
        for variable, value in replacements.items():
            item = item.replace('${' + variable + '}', str(value))
            if isinstance(value, int) and item == str(value):
                # The source type was int and the item has been completely substituted
                # -> Return int type
                return int(value)

        # Search for any missing variables
        if isinstance(item, str):
            self._missing_vars.extend(self.VAR_PATTERN.findall(item))
        return item

    def parent(self, template_processor: YmlTemplateProcessor):
        """
        Inherits all replacements from the given processor.
        If the same value is defined in this and the parent, the definition of the this processor will override
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
