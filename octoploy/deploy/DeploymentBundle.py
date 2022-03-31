from __future__ import annotations

import os

import yaml

from octoploy.deploy.OcObjectDeployer import OcObjectDeployer
from octoploy.processing.DataPreProcessor import DataPreProcessor
from octoploy.processing.OcObjectMerge import OcObjectMerge
from octoploy.processing.YmlTemplateProcessor import YmlTemplateProcessor
from octoploy.utils.Log import Log
from octoploy.utils.YmlWriter import YmlWriter


class DeploymentBundle(Log):
    """
    Holds all objects of a single deployment
    """

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
        item_kind = data.get('kind', '').lower()
        if item_kind == '':
            self.log.info('Unknown object kind: ' + str(data))
            return
        if item_kind == 'Secret'.lower():
            self.log.info('Secrets are ignored')
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

    def deploy(self, deploy_runner: OcObjectDeployer):
        """
        Deploys all object
        :param deploy_runner: Deployment runner which should be used
        """
        deploy_runner.select_project()

        # First sort the objects
        # we want deploymentconfigs to be the last items since a config change might
        # have an impact
        def sorting(x):
            object_kind = x['kind'].lower()
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
