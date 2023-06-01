from typing import Dict, Optional


class BaseObj:
    api_version: str
    kind: str
    name: Optional[str]
    namespace: Optional[str]
    metadata: Dict[str, any]

    def __init__(self, data: Dict[str, any]):
        self.data = data
        self.kind = data['kind']
        self.api_version = data['apiVersion']

        self.metadata = data.get('metadata', {})
        self.name = self.metadata.get('name', None)
        self.namespace = self.metadata.get('namespace', None)

    def get_fqn(self) -> str:
        """
        Returns the complete name of this object, including the group and kind
        :return: Name
        """
        group = self.get_group()
        if group is None:
            return f'{self.kind}/{self.name}'

        return f'{self.kind}.{group}/{self.name}'

    def get_group(self) -> Optional[str]:
        """
        Returns the group part of the api version.
        For example "networking.k8s.io"
        :return: Group or None
        """
        segments = self.api_version.split('/')
        if len(segments) < 2:
            # Plain version
            return None
        return segments[0]

    def is_kind(self, kind: str) -> bool:
        if self.kind is None:
            return False
        return self.kind.lower() == kind.lower()

    def require_kind(self, kind: str):
        if not self.is_kind(kind):
            raise ValueError(f'Object is not of kind {kind}')
