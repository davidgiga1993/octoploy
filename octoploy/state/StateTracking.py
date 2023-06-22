from __future__ import annotations

from typing import Dict, List, Optional

import yaml

from octoploy.api.Oc import K8sApi
from octoploy.k8s.BaseObj import BaseObj
from octoploy.utils.Log import Log
from octoploy.utils.YmlWriter import YmlWriter


class ObjectState:
    fqn: str
    """
    Fully qualified name of the object in the format
    kind.group/name
    """

    visited: bool
    """
    Transient flag to indicate if the object has been visited by octoploy
    """

    def __init__(self):
        self.context: str = ''
        self.namespace: str = ''

        self.fqn = ''

        self.hash = ''
        self.visited = False

    def update_from_key(self, key: str):
        segments = key.split('/', 2)
        if len(segments) < 3:
            raise ValueError(f'Invalid key, must be 3 segments long {key}')

        self.context = segments[0]
        self.namespace = segments[1]
        self.fqn = segments[2]

    def parse(self, data: Dict[str, str]) -> ObjectState:
        self.context = data.get('context')
        self.namespace = data.get('namespace')
        self.fqn = data.get('fqn')
        if self.context is None or self.namespace is None or self.fqn is None:
            raise ValueError(f'Corrupt octoploy state, could not parse {data}')

        self.hash = data.get('hash', '')
        return self

    def to_dict(self) -> Dict[str, str]:
        return {
            'context': self.context,
            'namespace': self.namespace,
            'fqn': self.fqn,
            'hash': self.hash,
        }

    def get_key(self) -> str:
        return f'{self.context}/{self.namespace}/{self.fqn}'


class StateTracking(Log):
    """
    Stores the objects that have been deployed with octoploy.
    This allows octoploy to detect renamed / deleted objects.
    """
    CM_NAME = 'octoploy-state'
    _k8s_api: K8sApi
    _state: Dict[str, ObjectState]

    def __init__(self, api: K8sApi, name_suffix: str = ''):
        super().__init__()
        self._k8s_api = api
        self._cm_name = self.CM_NAME + name_suffix
        self._state = {}

    def restore(self, namespace: str):
        item = self._k8s_api.get(f'ConfigMap/{self._cm_name}', namespace=namespace)
        if item is None:
            return
        cm = item.data
        state_data_str = cm.get('data', {}).get('state', '')
        state_data = yaml.safe_load(state_data_str)
        if state_data is None:
            return

        for state_obj in state_data:
            object_state = ObjectState().parse(state_obj)
            self._state[object_state.get_key()] = object_state

    def store(self, namespace: str):
        self.log.debug(f'Persisting state in ConfigMap {self._cm_name}')

        states = []
        for object_state in self._state.values():
            states.append(object_state.to_dict())

        data = {
            'kind': 'ConfigMap',
            'apiVersion': 'v1',
            'metadata': {
                'name': self._cm_name
            },
            'data': {
                'state': YmlWriter.dump(states)
            }
        }
        yml = YmlWriter.dump(data)
        self._k8s_api.apply(yml, namespace=namespace)

    def add(self, object_state: ObjectState):
        self._state[object_state.get_key()] = object_state

    def remove(self, object_state: ObjectState):
        del self._state[object_state.get_key()]

    def remove_key(self, key: str):
        del self._state[key]

    def get_items(self, prefix: str) -> List[ObjectState]:
        """
        Returns all state items which start with the given prefix
        :param prefix: Prefix
        :return: Items
        """
        items = []
        for value in list(self._state.values()):
            key = value.get_key()
            if not key.startswith(prefix):
                continue
            items.append(value)
        return items

    def get_not_visited(self, context: str) -> List[ObjectState]:
        """
        Returns all objects which have not been visited
        :param context: Context
        :return: Objects
        """
        items = []
        for object_state in self._state.values():
            if not object_state.visited and object_state.context == context:
                items.append(object_state)
        return items

    def get_state(self, context_name: str, k8s_object: BaseObj) -> Optional[ObjectState]:
        state = self._k8s_to_state(context_name, k8s_object)
        return self._state.get(state.get_key())

    def visit(self, context_name: str, k8s_object: BaseObj, hash_val: str, only_update: bool = False):
        """
        Marks the given object as "visited".
        If the object is not yet in the state it will be added
        :param context_name: Name of the state context
        :param k8s_object: Kubernetes object
        :param hash_val: The new hash value of the object.
        :param only_update: True if the state should only be updated and not added if not existing
        """
        state = self._k8s_to_state(context_name, k8s_object)
        existing_state = self._state.get(state.get_key())
        if existing_state is None:
            if only_update:
                return
            state.hash = hash_val
            self._state[state.get_key()] = state
            return
        existing_state.hash = hash_val
        existing_state.visited = True

    def visit_only(self, context_name: str, k8s_object):
        """
        Marks the given object as "visited" if already in the state
        """
        state = self._k8s_to_state(context_name, k8s_object)
        existing_state = self._state.get(state.get_key())
        if existing_state is not None:
            existing_state.visited = True

    def print(self):
        self.log.info(f'State content of ConfigMap {self._cm_name}')
        for key, value in self._state.items():
            self.log.info('|- ' + value.get_key())

    @staticmethod
    def _k8s_to_state(context_name: str, k8s_object: BaseObj) -> ObjectState:
        # At this point we always have a namespace set for the object
        state = ObjectState()
        state.context = context_name
        state.namespace = k8s_object.namespace
        state.fqn = k8s_object.get_fqn()
        state.visited = True
        return state
