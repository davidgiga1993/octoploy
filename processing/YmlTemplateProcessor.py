from config.Config import AppConfig, RootConfig


class YmlTemplateProcessor:
    """
    Processes yml files by replacing any string placeholders
    """

    def __init__(self, root_config: RootConfig, app_config: AppConfig):
        self._root_config = root_config  # type: RootConfig
        self._app_config = app_config  # type: AppConfig

    def process(self, data: dict):
        """
        Processes the app data

        :param data: Data of the app, the data will be modified in place
        """
        replacements = self._app_config.get_replacements()
        self._walk_dict(replacements, data)

    def _walk_dict(self, replacements, data: dict):
        for key, obj in data.items():
            data[key] = self._walk_item(replacements, obj)
        return data

    def _walk_item(self, replacements, obj):
        if isinstance(obj, list):
            for idx, item in enumerate(obj):
                obj[idx] = self._walk_item(replacements, item)
            return obj

        if isinstance(obj, str):
            return self._replace(obj, replacements)

        if isinstance(obj, dict):
            return self._walk_dict(replacements, obj)
        return obj

    def _replace(self, item: str, replacements):
        for variable, value in replacements.items():
            item = item.replace('${' + variable + '}', value)
        return item
