from __future__ import annotations

import os
from typing import List

import yaml

from octoploy.config.Config import RootConfig, AppConfig, RunMode
from octoploy.deploy.DeploymentBundle import DeploymentBundle
from octoploy.deploy.K8sObjectDeployer import K8sObjectDeployer
from octoploy.processing.YmlTemplateProcessor import YmlTemplateProcessor
from octoploy.utils.Errors import SkipObject
from octoploy.utils.Log import Log
from octoploy.utils.Yml import Yml


class AppDeployment:
    """
    Deploys a single application (aka all yml files inside an app directory)
    """

    def __init__(self, root_config: RootConfig, app_config: AppConfig, mode: RunMode):
        self._root_config = root_config
        self._app_config = app_config
        self._mode = mode

    def deploy(self):
        """
        Deploys all instances of the app
        """
        if self._mode.out_file is not None:
            if os.path.isfile(self._mode.out_file):
                os.remove(self._mode.out_file)

        factory = AppDeployRunnerFactory(self._root_config, self._mode)
        runners = factory.create(self._app_config)
        for runner in runners:
            runner.deploy()


class AppDeployRunnerFactory:
    """
    Creates AppDeployRunner objects
    """

    def __init__(self, root_config: RootConfig, mode: RunMode):
        self._root_config = root_config
        self._mode = mode

    def create(self, root_app_config: AppConfig) -> List[AppDeployRunner]:
        """
        Creates deployment runner instances for the given app
        :param root_app_config: App for which the instances should be created
        """
        runners = []
        for app_config in root_app_config.get_for_each():
            runner = AppDeployRunner(self._root_config, app_config, mode=self._mode)
            runners.append(runner)
        return runners


class AppDeployRunner(Log):
    """
    Executes the deployment of a single app
    """

    def __init__(self, root_config: RootConfig, app_config: AppConfig, mode: RunMode = RunMode()):
        super().__init__()
        self._root_config = root_config
        self._app_config = app_config
        self._bundle = DeploymentBundle(self._root_config.get_pre_processor())
        self._mode = mode

    def deploy(self):
        """
        Deploys all items for the given app
        """
        if not self._app_config.enabled():
            raise ValueError('App is disabled')
        if self._app_config.is_template():
            raise ValueError("App is a template and can't be deployed")

        # Resolve all templating references
        template_processor = self._app_config.get_template_processor()
        template_processor.parent(self._root_config.get_template_processor())

        self._apply_templates(self._app_config.get_pre_template_refs(), template_processor)
        self._load_files(self._app_config.get_config_root(), template_processor)
        self._load_extra_configmaps(template_processor)
        self._apply_templates(self._app_config.get_post_template_refs(), template_processor)

        # Additional processing
        tree_processors = self._root_config.get_yml_processors()
        skipped_objects = []
        for processor in tree_processors:
            for k8s_object in self._bundle.objects:
                try:
                    processor.process(k8s_object)
                except SkipObject as e:
                    self.log.warning(f'Skipping object: {e}')
                    skipped_objects.append(k8s_object)

        for k8s_object in skipped_objects:
            # Mark in state as "visited" so the object doesn't get deleted on k8s side
            self._root_config.get_state().visit(self._app_config.get_name(), k8s_object, k8s_object.get_hash(),
                                                only_update=True)
            self._bundle.objects.remove(k8s_object)

        api = self._root_config.create_api()
        if self._mode.out_file is not None:
            self._bundle.dump_objects(self._mode.out_file)

        if self._mode.dry_run:
            return

        self.log.info(f'Checking {self._app_config.get_name()}')
        object_deployer = K8sObjectDeployer(self._root_config, api, self._app_config, mode=self._mode)
        self._bundle.deploy(object_deployer)

    def _apply_templates(self, template_names: List[str], template_processor: YmlTemplateProcessor):
        """
        Deploys all referenced templates (recursively)
        """
        for template_name in template_names:
            template = self._root_config.load_app_config(template_name)
            if not template.is_template():
                raise ValueError(f'Referenced app {template_name} is not declared as template')
            if not template.enabled():
                self.log.warning(f'Template {template_name} is disabled, skipping')
                return

            child_template_processor = YmlTemplateProcessor(template)
            # Inherit all vars from the previous template processor
            # The child processor is a parent from a config perspective
            # since its configuration will be overwritten by the previous template
            child_template_processor.child(template_processor)

            # The template might reference other templates
            # -> Recursively deploy them
            self._apply_templates(template.get_pre_template_refs(), child_template_processor)
            self._load_files(template.get_config_root(), child_template_processor)
            self._apply_templates(template.get_post_template_refs(), child_template_processor)

    def _load_files(self, root: str, template_processor: YmlTemplateProcessor):
        """
        Loads all yml files inside the given folder
        :param root: Path to the root of the configs folder
        """
        for item in os.listdir(root):
            path = os.path.join(root, item)
            if not os.path.isfile(path) or not item.endswith('.yml') or item.startswith('_'):
                continue
            try:
                docs = Yml.load_docs(path)
            except yaml.parser.ParserError as e:
                self.log.error(f'Could not parse {path} {e}')
                raise
            for doc in docs:
                self._bundle.add_object(doc, template_processor)

    def _load_extra_configmaps(self, template_processor: YmlTemplateProcessor):
        """
        Loads all defined file based configmaps
        :param template_processor: Template processor which should be applied
        """
        for config in self._app_config.get_config_maps():
            cm_object = config.build_object(self._app_config.get_config_root())
            self._bundle.add_object(cm_object.data, None if cm_object.disable_templating else template_processor)
