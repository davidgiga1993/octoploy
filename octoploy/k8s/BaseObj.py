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

    def is_kind(self, kind: str) -> bool:
        if self.kind is None:
            return False
        return self.kind.lower() == kind.lower()

    def require_kind(self, kind: str):
        if not self.is_kind(kind):
            raise ValueError(f'Object is not of kind {kind}')
