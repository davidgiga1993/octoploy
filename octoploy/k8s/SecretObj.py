from typing import Dict

from octoploy.k8s.BaseObj import BaseObj


class SecretObj(BaseObj):
    def __init__(self, data: Dict[str, any]):
        super().__init__(data)
        self.require_kind('secret')
        self.base64_data = data.get('data', {})
        self.string_data = data.get('stringData', {})

