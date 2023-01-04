from __future__ import annotations
from typing import Dict, List, Optional

from octoploy.k8s.BaseObj import BaseObj

from octoploy.utils.YmlWriter import YmlWriter
from octoploy.utils.Log import Log

from octoploy.api.Oc import K8sApi


class ObjectState:
    def __init__(self):
        self.context = ''
        self.name = ''
        self.api_version = ''
        self.kind = ''
        self.namespace: Optional[str] = None
        self.visited = False
        """
        Transient flag to indicate if the object has been visited by octoploy
        """

    def parse(self, data: Dict[str, str]) -> ObjectState:
        self.context = data['context']
        self.namespace = data['namespace']
        self.api_version = data['apiVersion']
        self.kind = data['kind']
        self.name = data['name']
        return self

    def to_dict(self) -> Dict[str, str]:
        return {
            'name': self.name,
            'apiVersion': self.api_version,
            'kind': self.kind,
            'context': self.context,
            'namespace': self.namespace,
        }

    def get_key(self) -> str:
        return f'{self.context}*{self.api_version}|{self.kind}|{self.namespace}/{self.name}'


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
        cm = item.data
        state_data = cm.get('data', {}).get('state', [])
        for state_obj in state_data:
            object_state = ObjectState().parse(state_obj)
            self._state[object_state.get_key()] = object_state

    def store(self, namespace: str):
        self.log.debug(f'Persisting state in cm {self._cm_name}')

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
                'state': states
            }
        }
        yml = YmlWriter.dump(data)
        self._k8s_api.apply(yml, namespace=namespace)

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

    def visit(self, context_name: str, k8s_object: BaseObj):
        """
        Marks the given object as "visited".
        If the object is not yet in the state it will be added
        :param context_name: Name of the state context
        :param k8s_object: Kubernetes object
        """
        state = self._k8s_to_state(context_name, k8s_object)
        existing_state = self._state.get(state.get_key())
        if existing_state is None:
            self._state[state.get_key()] = state
            return
        existing_state.visited = True

    def remove(self, object_state: ObjectState):
        del self._state[object_state.get_key()]

    def _k8s_to_state(self, context_name: str, k8s_object: BaseObj) -> ObjectState:
        api_version = k8s_object.api_version
        kind = k8s_object.kind
        name = k8s_object.name

        state = ObjectState()
        state.namespace = k8s_object.namespace
        state.context = context_name
        state.api_version = api_version
        state.kind = kind
        state.name = name
        state.visited = True
        return state
