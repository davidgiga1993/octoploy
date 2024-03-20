from abc import abstractmethod
from typing import Optional

from octoploy.api.Kubectl import K8sApi
from octoploy.k8s.BaseObj import BaseObj


class DeploymentMode:
    """
    Defines how an object should be deployed
    """
    _api: K8sApi

    def use_api(self, api: K8sApi):
        self._api = api

    @abstractmethod
    def deploy(self, k8s_object: BaseObj, existing_object: Optional[BaseObj], namespace: str):
        pass


class ReplaceDeploymentMode(DeploymentMode):
    """
    Replace the object
    """

    def deploy(self, k8s_object: BaseObj, existing_object: Optional[BaseObj], namespace: str):
        self._api.replace(k8s_object.as_string(), namespace=namespace)


class ApplyDeploymentMode(DeploymentMode):
    """
    Apply the object
    """

    def deploy(self, k8s_object: BaseObj, existing_object: Optional[BaseObj], namespace: str):
        self._api.apply(k8s_object.as_string(), namespace=namespace)
