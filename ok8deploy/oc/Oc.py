import json
import platform
import subprocess
from abc import abstractmethod
from typing import Optional, List

from octoploy.oc.Model import ItemDescription, PodData
from octoploy.utils.Log import Log


class K8Api(Log):
    def __init__(self):
        super().__init__('K8Api')

    @abstractmethod
    def tag(self, source: str, dest: str):
        """
        Tags the given image stream (OC only!)
        :param source: Source tag
        :param dest: Destination tag
        """
        raise NotImplemented

    def get_namespaces(self) -> List[str]:
        """
        Returns all namespaces
        :return: Namespaces
        """

    @abstractmethod
    def get(self, name: str) -> Optional[ItemDescription]:
        """
        Returns the given item
        :param name: Name
        :return: Data (if found)
        """
        raise NotImplemented

    @abstractmethod
    def apply(self, yml: str) -> str:
        """
        Applies the given yml file
        :param yml: Yml file
        :return: Stdout
        """
        raise NotImplemented

    @abstractmethod
    def get_pod(self, dc_name: str = None, pod_name: str = None) -> Optional[PodData]:
        """
        Returns a pod by deployment name or pod name
        :param dc_name: Deployment name
        :param pod_name: Pod name
        :return: Pod (if found)
        :raise Exception: More than one pod found
        """
        raise NotImplemented

    @abstractmethod
    def get_pods(self, dc_name: str = None, pod_name: str = None) -> List[PodData]:
        """
        Returns all pods which match the given deployment name or pod name
        :param dc_name: Deployment name
        :param pod_name: Pod name
        :return: Pods
        """
        raise NotImplemented

    @abstractmethod
    def rollout(self, name: str):
        """
        Re-Deploys the latest DC with the given name
        :param name: Deployment name
        """
        raise NotImplemented

    @abstractmethod
    def exec(self, pod_name: str, cmd: str, args: List[str]):
        """
        Executes a command in the given pod
        :param pod_name: Pod name
        :param cmd: Command
        :param args: Arguments
        """
        raise NotImplemented

    @abstractmethod
    def project(self, project: str):
        """
        Changes the default project / namespace
        :param project: Project
        """
        raise NotImplemented

    @abstractmethod
    def switch_context(self, context: str):
        """
        Changes the configuration context
        :param context: Context
        """
        raise NotImplemented

    @abstractmethod
    def annotate(self, name: str, key: str, value: str):
        """
        Add / updates the annotation at the given item
        :param name: Name
        :param key: Annotation key
        :param value: Annotation value
        """
        raise NotImplemented


class Oc(K8Api):
    def get_namespaces(self) -> List[str]:
        lines = self._exec(['get', 'namespaces', '-o', 'name'])
        return lines.splitlines()

    def tag(self, source: str, dest: str):
        self._exec(['tag', source, dest], print_out=True)

    def get(self, name: str) -> Optional[ItemDescription]:
        try:
            json_str = self._exec(['get', name, '-o', 'json'])
        except Exception as e:
            if 'NotFound' in str(e):
                return None
            raise

        return ItemDescription(json.loads(json_str))

    def apply(self, yml: str) -> str:
        return self._exec(['apply', '-f', '-'], stdin=yml)

    def get_pod(self, dc_name: str = None, pod_name: str = None) -> Optional[PodData]:
        pods = self.get_pods(dc_name=dc_name, pod_name=pod_name)
        if len(pods) == 0:
            return None
        if len(pods) > 1:
            raise Exception('More than one match found')
        return pods[0]

    def get_pods(self, dc_name: str = None, pod_name: str = None) -> List[PodData]:
        pods = []
        json_str = self._exec(['get', 'pods', '-o', 'json'])
        data = json.loads(json_str)
        items = data['items']
        for pod in items:
            metadata = pod['metadata']
            version = int(metadata['annotations'].get('openshift.io/deployment-config.latest-version', 0))
            labels = metadata.get('labels', {})
            name = metadata['name']
            status = pod['status'].get('containerStatuses', [{}])
            if len(status) > 0:
                status = status[0]

            pod_data = PodData()
            pod_data.name = name
            pod_data.version = version
            pod_data.ready = status.get('ready', False)
            pod_data.set_labels(labels)

            if pod_name is not None and pod_data.name != pod_name:
                continue
            if dc_name is not None and pod_data.deployment_config != dc_name:
                continue
            pods.append(pod_data)

        return pods

    def rollout(self, name: str):
        """
        Re-Deploys the latest DC with the given name
        :param name: DC name
        """
        self._exec(['rollout', 'latest', name])

    def exec(self, pod_name: str, cmd: str, args: List[str]):
        proc_args = ['exec', pod_name, '--', cmd]
        proc_args.extend(args)
        self._exec(proc_args, print_out=True)

    def project(self, project: str):
        self._exec(['project', project])

    def switch_context(self, context: str):
        raise NotImplemented('Not available for openshift')

    def annotate(self, name: str, key: str, value: str):
        self._exec(['annotate', '--overwrite=true', name, key + '=' + value])

    def _exec(self, args, print_out: bool = False, stdin: str = None) -> str:
        args.insert(0, self._get_bin())
        if print_out:
            print(str(args))

        stdin_bytes = None
        if stdin is not None:
            stdin_bytes = stdin.encode('utf-8')

        self.log.debug('Executing ' + str(args))
        result = subprocess.run(args, capture_output=True, input=stdin_bytes)
        if result.returncode != 0:
            if stdin is not None:
                print(stdin.replace('\\n', '\n'))
            raise Exception('Failed: ' + str(result.stderr.decode('utf-8')))
        output = result.stdout.decode('utf-8')
        if print_out:
            print(output)
        return output

    def _get_bin(self) -> str:
        if platform.system() == 'Windows':
            return 'oc.exe'
        return 'oc'


class K8(Oc):
    _namespace: str = ''

    def rollout(self, name: str):
        self._exec(['rollout', 'restart', 'deployments', name])

    def tag(self, source: str, dest: str):
        raise NotImplemented('Not available for k8')

    def project(self, project: str):
        self._namespace = project

    def switch_context(self, context: str):
        self._exec(['config', 'use-context', context])

    def _exec(self, args, print_out: bool = False, stdin: str = None):
        if self._namespace != '':
            args.append('--namespace=' + self._namespace)
        return super()._exec(args, print_out, stdin)

    def _get_bin(self) -> str:
        if platform.system() == 'Windows':
            return 'kubectl.exe'
        return 'kubectl'
