from abc import abstractmethod
from typing import Dict, Optional

from octoploy.k8s.BaseObj import BaseObj


class TreeProcessor:
    @abstractmethod
    def process(self, k8s_object: BaseObj):
        """
        Processes the tree

        :param k8s_object: K8s object
        :raises: SkipObject: The object should be skipped
        """
        pass

    def process_object(self, data: Dict[str, any], parent: Dict[str, any], key: str) -> Optional[Dict[str, any]]:
        """
       Processes a node of the tree
       :param data: Object
       :param parent: Parent holding the object
       :param key: Key of the object
       :return: New value or None if the parent should not be updated
       """
        return data

    def process_str(self, value: str, parent: Dict[str, any], key: str) -> Optional[any]:
        """
        Processes a string leaf of the tree
        :param value: Value
        :param parent: Parent holding the value
        :param key: Key of the value
        :return: New value or None if the value should not be updated
        """
        return value


class TreeWalker:
    """
    Walks through dictionary trees
    """

    def __init__(self, processor: TreeProcessor):
        self.processor = processor

    def walk(self, data: Dict[str, any]):
        self._walk(data)

    def _walk(self, data: Dict[str, any]):
        for key in list(data.keys()):
            value = data[key]
            new_val = self._process_item(value, data, key)
            if new_val is None:
                continue
            data[key] = new_val

    def _process_item(self, value, data, key) -> any:
        if isinstance(value, list):
            for idx, list_item in enumerate(value):
                value[idx] = self._process_item(list_item, data, key)
            return value

        if isinstance(value, str):
            return self.processor.process_str(value, data, key)

        if isinstance(value, dict):
            new_val = self.processor.process_object(value, data, key)
            if new_val is None:
                return None
            self._walk(new_val)
            return new_val
        return value
