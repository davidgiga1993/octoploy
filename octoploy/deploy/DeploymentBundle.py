from __future__ import annotations

import os
from typing import List

import yaml

from octoploy.deploy.K8sObjectDeployer import K8sObjectDeployer
from octoploy.k8s.BaseObj import BaseObj
from octoploy.processing.DataPreProcessor import DataPreProcessor
from octoploy.processing.K8sObjectMerge import K8sObjectMerge
from octoploy.processing.YmlTemplateProcessor import YmlTemplateProcessor
from octoploy.utils.Log import Log
from octoploy.utils.YmlWriter import YmlWriter


class DeploymentBundle(Log):
    """
    Holds all objects of a single deployment (aka everything inside one folder)
    """
    objects: List[BaseObj]

    def __init__(self, pre_processor: DataPreProcessor):
        super().__init__()
        self.objects = []  # All objects which should be deployed
        self._pre_processor = pre_processor

    def add_object(self, data: dict, template_processor: YmlTemplateProcessor):
        """
        Adds a new object which should be deployed
        :param data: Object
        :param template_processor: Template processor which should be used
        """
        k8s_object = BaseObj(data)
        if k8s_object.kind is None:
            self.log.info('Unknown object kind: ' + str(data))
            return

        # Pre-process any variables
        if template_processor is not None:
            template_processor.process(k8s_object)

        merger = K8sObjectMerge()
        # Check if the new data can be merged into any existing objects
        for item in self.objects:
            if merger.merge(item, k8s_object):
                # Data has been merged
                return

        self._pre_processor.process(data)
        self.objects.append(k8s_object)

    def deploy(self, deploy_runner: K8sObjectDeployer):
        """
        Deploys all objects in this bundle
        :param deploy_runner: Deployment runner which should be used
        """
        # First sort the objects, we want "deployments" to be the last object type
        # so all prerequisites are available
        def sorting(x: BaseObj):
            if x.is_kind('DeploymentConfig') or x.is_kind('Deployment'):
                return 1
            return 0

        self.objects.sort(key=sorting)
        for item in self.objects:
            deploy_runner.add_object(item)

        deploy_runner.execute()

    def dump_objects(self, path: str):
        """
        Very crude method for dumping the objects to a yml file.
        If the file does already exist the content will be appended
        :param path: Path to a file
        """
        all_objects = []
        if os.path.isfile(path):
            with open(path) as f:
                data = yaml.load_all(f, Loader=yaml.FullLoader)
                for doc in data:
                    all_objects.append(doc)

        all_objects.extend([x.data for x in self.objects])
        with open(path, 'w') as file:
            YmlWriter.dump_all(all_objects, file)
