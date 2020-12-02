from typing import Optional, Dict


class DictUtils:
    @staticmethod
    def get(data: Optional[dict], path: str):
        if data is None:
            return None

        for part in path.split('.'):
            if part not in data:
                return None
            data = data[part]
        return data

    @staticmethod
    def set(data: Dict, path: str, value: any):
        parts = path.split('.')
        for part in parts[:-1]:
            if part not in data:
                data[part] = {}
            data = data[part]
        data[parts[-1]] = value
