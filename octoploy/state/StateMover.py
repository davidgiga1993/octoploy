from typing import Optional, Tuple

from octoploy.config.Config import RootConfig, RunMode
from octoploy.state.StateTracking import StateTracking
from octoploy.utils.Log import Log


class StateMover(Log):
    def __init__(self, source_config: RootConfig):
        super().__init__(__name__)
        self._sourceConfig = source_config

    def move(self, source: str, dest: str, dest_configmap: Optional[str]):
        """
        Moves the state from the given source to the given destination
        :param source: Source
        :param dest: Destination
        :param dest_configmap: Different configmap which should receive the state
        """
        if source.count('/') != dest.count('/'):
            raise ValueError('Source and destination point to different path depths')

        run_mode = RunMode()
        self._sourceConfig.initialize_state(run_mode)
        source_state = self._sourceConfig.get_state()

        items_to_be_moved = source_state.get_items(source)
        for item in items_to_be_moved:
            key = item.get_key()
            target = key.replace(source, dest)
            self.log.info(f'Moving {key} to {target}')
            item.update_from_key(target)
            source_state.remove_key(key)

        target_state = source_state
        target_namespace = self._sourceConfig.get_namespace_name()
        if dest_configmap is not None:
            target_state, target_namespace = self._get_state_from_cm(dest_configmap)

        for item in items_to_be_moved:
            target_state.add(item)

        if len(items_to_be_moved) == 0:
            self.log.warning('No items moved')
            return

        # First persist the target to prevent data loss on error
        if target_state != source_state:
            target_state.store(target_namespace)
        source_state.store(self._sourceConfig.get_namespace_name())

    def _get_state_from_cm(self, configmap: str) -> Tuple[StateTracking, str]:
        namespace = self._sourceConfig.get_namespace_name()
        segments = configmap.split('/', 1)
        if len(segments) == 2:
            namespace = segments[0]
            cm_suffix = segments[1]
        else:
            cm_suffix = segments[0]

        api = self._sourceConfig.create_api()
        state = StateTracking(api, name_suffix=cm_suffix)
        state.restore(namespace)
        return state, namespace
