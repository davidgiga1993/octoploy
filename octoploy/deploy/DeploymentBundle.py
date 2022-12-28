from __future__ import annotations

import base64
import os
from typing import List, Dict

import yaml

from octoploy.deploy.K8sObjectDeployer import K8sObjectDeployer
from octoploy.k8s.BaseObj import BaseObj
from octoploy.processing.DataPreProcessor import DataPreProcessor
from octoploy.processing.DecryptionProcessor import DecryptionProcessor
from octoploy.processing.OcObjectMerge import OcObjectMerge
from octoploy.processing.YmlTemplateProcessor import YmlTemplateProcessor
from octoploy.utils.Log import Log
from octoploy.utils.YmlWriter import YmlWriter


class DeploymentBundle(Log):
    """
    Holds all objects of a single deployment (aka everything inside one folder)
    """
    objects: List[Dict[str, any]]

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
            template_processor.process(data)

        merger = OcObjectMerge()
        # Check if the new data can be merged into any existing objects
        for item in self.objects:
            if merger.merge(item, data):
                # Data has been merged
                return

        self._pre_processor.process(data)
        self.objects.append(data)

    def deploy(self, deploy_runner: K8sObjectDeployer):
        """
        Deploys all object
        :param deploy_runner: Deployment runner which should be used
        """
        deploy_runner.select_namespace()

        # First sort the objects, we want "deployments" to be the last object type
        # so all prerequisites are available
        def sorting(x):
            k8s_object = BaseObj(x)
            object_kind = k8s_object.kind.lower()
            if object_kind == 'DeploymentConfig'.lower() or \
                    object_kind == 'Deployment'.lower():
                return 1
            return 0

        self.objects.sort(key=sorting)
        for item in self.objects:
            deploy_runner.deploy_object(item)

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

        all_objects.extend(self.objects)
        with open(path, 'w') as file:
            YmlWriter.dump_all(all_objects, file)
