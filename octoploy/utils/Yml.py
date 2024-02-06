from typing import Dict, List

import yaml


class Yml:
    @staticmethod
    def load_docs(path: str) -> List[Dict[any, any]]:
        docs = []
        with open(path) as f:
            data = yaml.load_all(f, Loader=yaml.FullLoader)
            for doc in data:
                if doc is None:
                    # Empty block
                    continue
                docs.append(doc)
        return docs

    @classmethod
    def load_str(cls, yml: str) -> Dict[str, any]:
        return yaml.load(yml, Loader=yaml.FullLoader)
