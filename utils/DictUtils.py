from typing import Optional


class DictUtils:
    @staticmethod
    def get(items: Optional[dict], path: str):
        if items is None:
            return None

        for part in path.split('.'):
            if part not in items:
                return None
            items = items[part]
        return items
