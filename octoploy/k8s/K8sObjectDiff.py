from typing import Dict, List

from octoploy.utils.YmlWriter import YmlWriter

from octoploy.api.Kubectl import K8sApi
from octoploy.k8s.BaseObj import BaseObj
from octoploy.utils.Log import ColorFormatter


class K8sObjectDiff:
    """
    Creates nice to look at diffs of two yml files.
    This diff ignores any changes injected by k8s itself (e.g. status, timestamps, ..)
    """

    def __init__(self, k8s: K8sApi):
        self._api = k8s

    def print(self, current: BaseObj, new: BaseObj):
        """
        Prints a diff
        :param current: The current object in the cluster
        :param new: The new object
        """
        current_data = self._filter_injected(current.data)

        # Server side dry-run to get the same format / list sorting
        new = self._api.dry_run(YmlWriter.dump(new.data))
        new_data = self._filter_injected(new.data)
        self._print_diff(current_data, new_data, [])

    def _print_diff(self, current_data: Dict[str, any], new_data: Dict[str, any],
                    context: List[str]):
        if current_data is None:
            current_data = {}
        if new_data is None:
            new_data = {}
        all_keys = set(current_data.keys())
        all_keys.update(new_data.keys())
        all_keys = sorted(all_keys)

        for key in all_keys:
            current_entry = current_data.get(key)
            new_entry = new_data.get(key)
            self._print_value_diff(current_entry, new_entry, context + [key])

    def _print_value_diff(self, current_entry, new_entry, context):
        if isinstance(current_entry, list) or isinstance(new_entry, list):
            if current_entry is None:
                current_entry = []
            if new_entry is None:
                new_entry = []

            count = max(len(current_entry), len(new_entry))
            for i in range(count):
                current_val = None
                new_val = None
                if i < len(current_entry):
                    current_val = current_entry[i]
                if i < len(new_entry):
                    new_val = new_entry[i]
                self._print_value_diff(current_val, new_val, context + [f'[{i}]'])
            return

        if isinstance(current_entry, dict) or isinstance(new_entry, dict):
            self._print_diff(current_entry, new_entry, context)
            return
        if current_entry == new_entry:
            return

        if current_entry is None:
            # The entire tree will be added
            print(ColorFormatter.colorize(
                '+ ' + '.'.join(context) + f' = {new_entry}',
                ColorFormatter.green))
            return
        if new_entry is None:
            # The entire tree will be removed
            print(ColorFormatter.colorize(
                '- ' + '.'.join(context) + f' = {current_entry}',
                ColorFormatter.red))
            return

        print(ColorFormatter.colorize(
            '~ ' + '.'.join(context) + f' = {current_entry} -> {new_entry}',
            ColorFormatter.yellow))

    def _filter_injected(self, data: Dict[str, any]) -> Dict[str, any]:
        """Removes injected fields"""
        data = dict(data)  # Create a copy
        metadata = data.get('metadata', {})
        self._del(metadata, 'creationTimestamp')
        self._del(metadata, 'generation')
        self._del(metadata, 'resourceVersion')
        self._del(metadata, 'uid')
        self._del(metadata, 'finalizers')
        self._del(metadata.get('annotations', {}), 'kubectl.kubernetes.io/last-applied-configuration')
        self._del(metadata.get('annotations', {}), 'kubectl.kubernetes.io/restartedAt')
        self._del(data, 'status')
        return data

    @staticmethod
    def _del(data: Dict[str, any], key: str):
        if key in data:
            del data[key]
