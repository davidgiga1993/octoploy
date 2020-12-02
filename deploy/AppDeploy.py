from __future__ import annotations

import os
from typing import Optional, List

import yaml

from config.Config import RootConfig, AppConfig
from deploy.OcObjectDeployer import OcObjectDeployer
from processing.OcObjectMerge import OcObjectMerge
from processing.YmlTemplateProcessor import YmlTemplateProcessor


class DeploymentBundle:
    """
    Holds all objects of a single deployment
    """

    def __init__(self):
        self.objects = []  # All objects which should be deployed

    def add_object(self, data: dict, template_processor: YmlTemplateProcessor):
        """
        Adds a new object which should be deployed
        :param data: Object
        :param template_processor: Template processor which should be used
        """
        item_kind = data.get('kind', '').lower()
        if item_kind == '':
            print('Unknown object kind: ' + str(data))
            return
        if item_kind == 'Secret'.lower():
            print('Secrets are ignored')
            return
        if item_kind == 'PersistentVolumeClaim'.lower():
            print("PVCs are ignored")
            return

        # Pre-process any variables
        template_processor.process(data)

        merger = OcObjectMerge()
        # Check if the new data can be merged into any existing objects
        for item in self.objects:
            if merger.merge(item, data):
                # Data has been merged
                return

        self.objects.append(data)

    def deploy(self, deploy_runner: OcObjectDeployer):
        """
        Deploys all object
        :param deploy_runner: Deployment runner which should be used
        """

        # First sort the objects
        # we want deploymentconfigs to be the last items since a config change might
        # have an impact
        def sorting(x):
            if x['kind'].lower() == 'DeploymentConfig'.lower():
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
            yaml.dump_all(all_objects, file, default_flow_style=False, sort_keys=True)


class AppDeployment:
    """
    Deploys a single application
    """

    def __init__(self, root_config: RootConfig, app_config: AppConfig, dry_run: Optional[str]):
        self._root_config = root_config
        self._app_config = app_config
        self._dry_run = dry_run

    def deploy(self):
        """
        Deploys all instances of the app
        """
        if self._dry_run is not None:
            if os.path.isfile(self._dry_run):
                os.remove(self._dry_run)

        factory = AppDeployRunnerFactory(self._root_config, self._dry_run)
        runners = factory.create(self._app_config)
        for runner in runners:
            runner.deploy()


class AppDeployRunnerFactory:
    """
    Creates AppDeployRunner objects
    """

    def __init__(self, root_config: RootConfig, dry_run: Optional[str]):
        self._root_config = root_config
        self._dry_run = dry_run  # type: Optional[str]

    def create(self, root_app_config: AppConfig) -> List[AppDeployRunner]:
        """
        Creates deployment runner instances for the given app
        :param root_app_config: App for which the instances should be created
        """
        runners = []
        for app_config in root_app_config.get_for_each():
            runner = AppDeployRunner(self._root_config, app_config, dry_run=self._dry_run)
            runners.append(runner)
        return runners


class AppDeployRunner:
    """
    Executes the deployment of a single app
    """

    def __init__(self, root_config: RootConfig, app_config: AppConfig, dry_run: Optional[str] = None):
        self._root_config = root_config
        self._app_config = app_config
        self._bundle = DeploymentBundle()
        self._dry_run = dry_run  # type: Optional[str]

    def deploy(self):
        """
        Deploys all items for the given app
        """
        if not self._app_config.enabled():
            raise ValueError('App is disabled')
        if self._app_config.is_template():
            raise ValueError('App is a template and can\'t be deployed')

        root_template_processor = YmlTemplateProcessor(self._app_config)
        self._deploy_templates(self._app_config.get_pre_template_refs(), root_template_processor)
        self._load_files(self._app_config.get_config_root(), root_template_processor)
        self._deploy_extra_configmaps(root_template_processor)
        self._deploy_templates(self._app_config.get_post_template_refs(), root_template_processor)

        oc = self._root_config.create_oc()
        if self._dry_run is not None:
            self._bundle.dump_objects(self._dry_run)
            return

        oc.project(self._root_config.get_project())
        print('Deploying ' + self._app_config.get_dc_name())
        object_deployer = OcObjectDeployer(self._root_config, oc, self._app_config)
        self._bundle.deploy(object_deployer)

    def _deploy_templates(self, template_names: List[str], template_processor: YmlTemplateProcessor):
        """
        Deploys all referenced templates (recursively)
        """
        for template_name in template_names:
            print('Applying template: ' + template_name)
            template = self._root_config.load_app_config(template_name)
            if not template.is_template():
                raise ValueError('Referenced app ' + template_name + ' is not declared as template')
            if not template.enabled():
                print('Warning: Template ' + template_name + ' is disabled, skipping')
                return

            child_template_processor = YmlTemplateProcessor(template)
            # Inherit all vars from the previous template processor
            child_template_processor.inherit(template_processor)

            # The template might reference other templates
            # -> Recursively deploy them
            self._deploy_templates(template.get_pre_template_refs(), child_template_processor)
            self._load_files(template.get_config_root(), child_template_processor)
            self._deploy_templates(template.get_post_template_refs(), child_template_processor)

    def _load_files(self, root: str, template_processor: YmlTemplateProcessor):
        """
        Loads all yml files inside the given folder
        :param root: Path to the root of the configs folder
        """
        for item in os.listdir(root):
            path = os.path.join(root, item)
            if not os.path.isfile(path) or not item.endswith('.yml') or item.startswith('_'):
                continue

            with open(path, 'r') as stream:
                data = yaml.load_all(stream, Loader=yaml.FullLoader)
                for doc in data:
                    if doc is None:
                        # Empty block
                        continue
                    self._bundle.add_object(doc, template_processor)

    def _deploy_extra_configmaps(self, template_processor: YmlTemplateProcessor):
        """
        Deploys all defined file based configmaps
        :param template_processor: Template processor which should be applied
        """
        for config in self._app_config.get_config_maps():
            oc_obj = config.build_oc_obj(self._app_config.get_config_root())
            self._bundle.add_object(oc_obj, template_processor)
