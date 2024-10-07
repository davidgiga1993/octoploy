import difflib
from typing import Dict, List, Iterator

from octoploy.api.Kubectl import K8sApi
from octoploy.k8s.BaseObj import BaseObj
from octoploy.utils.Log import ColorFormatter
from octoploy.utils.YmlWriter import YmlWriter


class ValueMask:
    fields: List[List[str]] = []
    """
    Holds a list of context paths that should be masked
    """

    def __init__(self):
        self.fields = []

    def should_mask_value(self, context: List[str]) -> bool:
        for mask_path in self.fields:
            if len(mask_path) > len(context):
                continue
            # Check if the context path starts with the mask path
            if context[:len(mask_path)] == mask_path:
                return True
        return False


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
        mask = ValueMask()
        if current.is_kind('secret') or new.is_kind('secret'):
            mask.fields.append(['data'])
            mask.fields.append(['stringData'])
        current_data = self._filter_injected(current.data)

        # Server side dry-run to get the same format / list sorting
        new = self._api.dry_run(YmlWriter.dump(new.data))
        new_data = self._filter_injected(new.data)
        self._print_diff(current_data, new_data, [], mask)

    def _print_diff(self, current_data: Dict[str, any], new_data: Dict[str, any],
                    context: List[str], value_mask: ValueMask):
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
            self._print_value_diff(current_entry, new_entry, context + [key], value_mask)

    def _print_value_diff(self, current_entry, new_entry, context: List[str], value_mask: ValueMask):
        mask_value: bool = value_mask.should_mask_value(context)
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
                self._print_value_diff(current_val, new_val, context + [f'[{i}]'], value_mask)
            return

        if isinstance(current_entry, dict) or isinstance(new_entry, dict):
            self._print_diff(current_entry, new_entry, context, value_mask)
            return
        if current_entry == new_entry:
            return

        if mask_value:
            if current_entry is not None:
                current_entry = '***'
            if new_entry is not None:
                new_entry = '***'

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

        # If the entry is a multiline string, we create a proper diff
        if (isinstance(current_entry, str) and isinstance(new_entry, str) and
                ('\n' in current_entry or '\n' in new_entry)):
            delta = difflib.unified_diff(current_entry.splitlines(), new_entry.splitlines())
            print(ColorFormatter.colorize(
                '~ ' + '.'.join(context) + f':',
                ColorFormatter.yellow))
            self._print_text_diff(delta)
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

    @staticmethod
    def _print_text_diff(delta: Iterator[str]):
        for line in delta:
            line = line.strip('\n').strip()
            if line == '---' or line == '+++':
                continue
            color = ''
            if line.startswith('+'):
                color = ColorFormatter.green
            elif line.startswith('-'):
                color = ColorFormatter.red
            print(ColorFormatter.colorize('\t' + line, color))
