from octoploy.k8s.BaseObj import BaseObj
from octoploy.utils.DictUtils import DictUtils


class DataPreProcessor:
    def __init__(self):
        pass

    def process(self, yml):
        """
        Preprocesses the yml in place
        """


class OcToK8PreProcessor(DataPreProcessor):

    def process(self, yml):
        k8s_object = BaseObj(yml)
        if k8s_object.is_kind('DeploymentConfig'):
            yml['kind'] = 'Deployment'
            version = yml.get('apiVersion')
            if not version.startswith('apps/'):
                yml['apiVersion'] = 'apps/' + version

            name_selector = DictUtils.get(yml, 'spec.selector.name')
            if name_selector is not None:
                DictUtils.delete(yml, 'spec.selector.name')
                DictUtils.set(yml, 'spec.selector.matchLabels.app', name_selector)

            strategy_type = DictUtils.get(yml, 'spec.strategy.type')
            if strategy_type == 'Rolling':
                DictUtils.set(yml, 'spec.strategy.type', 'RollingUpdate')

            name = DictUtils.get(yml, 'spec.template.metadata.labels.name')
            if name is not None:
                DictUtils.delete(yml, 'spec.template.metadata.labels.name')
                DictUtils.set(yml, 'spec.template.metadata.labels.app', name)

            return
