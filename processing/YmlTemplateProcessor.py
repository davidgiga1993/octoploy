from __future__ import annotations

import re
from typing import Optional, Dict, List, Set

from config.Config import AppConfig
from utils.Errors import MissingParam


class YmlTemplateProcessor:
    """
    Processes yml files by replacing any string placeholders
    """

    VAR_PATTERN = re.compile(r'\${(.+)}')

    def __init__(self, app_config: AppConfig):
        self._missing_vars = []  # type: List[str]
        """
        List of all variables which have not been replace because
        there was no value defined for them
        """
        self._app_config = app_config  # type: AppConfig
        self._parent = None  # type: Optional[YmlTemplateProcessor]

    def process(self, data: dict):
        """
        Processes the app data

        :param data: Data of the app, the data will be modified in place
        :raise MissingParam: Gets raised if at least one parameter is not defined
        """
        replacements = self._get_replacements()
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
            raise MissingParam('The following params are not defined: ' + str(missing_params))

    def _get_params(self) -> Set[str]:
        """
        Returns all defined params
        :return: Param names
        """
        params = set(self._app_config.get_params())
        if self._parent is not None:
            params.update(self._parent._get_params())
        return params

    def _get_replacements(self) -> Dict[str, str]:
        """
        Returns all replacements handled by this processor, including all parent variables
        :return: Replacements
        """
        replacements = self._app_config.get_replacements()
        if self._parent is not None:
            replacements.update(self._parent._get_replacements())
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
        # Search for any missing variables
        matcher = self.VAR_PATTERN.findall(item)
        for missing in matcher:
            self._missing_vars.append(missing)
        return item

    def inherit(self, template_processor: YmlTemplateProcessor):
        """
        Inherits all replacements from the given processor.
        If the same value is defined the definition of the given processor will override
        the existing definition
        :param template_processor: Parent processor
        """
        self._parent = template_processor
