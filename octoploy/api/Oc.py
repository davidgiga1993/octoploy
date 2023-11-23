import json
import platform
import subprocess
from abc import abstractmethod
from typing import Optional, List

from octoploy.api.Model import ItemDescription, PodData
from octoploy.utils.Log import Log


class K8sApi(Log):
    def __init__(self):
        super().__init__('K8Api')

    @abstractmethod
    def tag(self, source: str, dest: str, namespace: Optional[str] = None):
        """
        Tags the given image stream (OC only!)
        :param source: Source tag
        :param dest: Destination tag
        :param namespace: Namespace
        """
        raise NotImplemented

    def get_namespaces(self) -> List[str]:
        """
        Returns all namespaces
        :return: Namespaces
        """

    @abstractmethod
    def get(self, name: str, namespace: Optional[str] = None) -> Optional[ItemDescription]:
        """
        Returns the given item
        :param name: Name
        :param namespace: Namespace
        :return: Data (if found)
        """
        raise NotImplemented

    @abstractmethod
    def apply(self, yml: str, namespace: Optional[str] = None) -> str:
        """
        Applies the given yml file
        :param yml: Yml file
        :param namespace: Namespace
        :return: Stdout
        """
        raise NotImplemented

    @abstractmethod
    def get_pod(self, dc_name: str = None, pod_name: str = None,
                namespace: Optional[str] = None) -> Optional[PodData]:
        """
        Returns a pod by deployment name or pod name
        :param dc_name: Deployment name
        :param pod_name: Pod name
        :param namespace: Namespace
        :return: Pod (if found)
        :raise Exception: More than one pod found
        """
        raise NotImplemented

    @abstractmethod
    def get_pods(self, dc_name: str = None, pod_name: str = None,
                 namespace: Optional[str] = None) -> List[PodData]:
        """
        Returns all pods which match the given deployment name or pod name
        :param dc_name: Deployment name
        :param pod_name: Pod name
        :param namespace: Namespace
        :return: Pods
        """
        raise NotImplemented

    @abstractmethod
    def rollout(self, name: str, namespace: Optional[str] = None):
        """
        Re-Deploys the latest DC with the given name
        :param name: Deployment name
        :param namespace: Namespace
        """
        raise NotImplemented

    @abstractmethod
    def exec(self, pod_name: str, cmd: str, args: List[str], namespace: Optional[str] = None):
        """
        Executes a command in the given pod
        :param pod_name: Pod name
        :param cmd: Command
        :param args: Arguments
        :param namespace: Namespace
        """
        raise NotImplemented

    @abstractmethod
    def switch_context(self, context: str):
        """
        Changes the configuration context
        :param context: Context which should be used
        """
        raise NotImplemented

    @abstractmethod
    def annotate(self, name: str, key: str, value: Optional[str], namespace: Optional[str] = None):
        """
        Add / updates the annotation at the given item
        :param name: Name
        :param key: Annotation key
        :param value: Annotation value
        :param namespace: Namespace
        """
        raise NotImplemented

    def delete(self, name: str, namespace: str):
        """
        Deletes the given item
        :param name: Name
        :param namespace: Namespace
        """
        raise NotImplemented


class Oc(K8sApi):
    def get_namespaces(self) -> List[str]:
        lines = self._exec(['get', 'namespaces', '-o', 'name'])
        return lines.splitlines()

    def tag(self, source: str, dest: str, namespace: Optional[str] = None):
        self._exec(['tag', source, dest], print_out=True, namespace=namespace)

    def get(self, name: str, namespace: Optional[str] = None) -> Optional[ItemDescription]:
        try:
            json_str = self._exec(['get', name, '-o', 'json'], namespace=namespace)
        except Exception as e:
            if 'NotFound' in str(e):
                return None
            raise

        return ItemDescription(json.loads(json_str))

    def apply(self, yml: str, namespace: Optional[str] = None) -> str:
        return self._exec(['apply', '-f', '-'], stdin=yml, namespace=namespace)

    def get_pod(self, dc_name: str = None, pod_name: str = None, namespace: Optional[str] = None) -> Optional[PodData]:
        pods = self.get_pods(dc_name=dc_name, pod_name=pod_name, namespace=namespace)
        if len(pods) == 0:
            return None
        if len(pods) > 1:
            raise Exception('More than one match found')
        return pods[0]

    def get_pods(self, dc_name: str = None, pod_name: str = None, namespace: Optional[str] = None) -> List[PodData]:
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

    def rollout(self, name: str, namespace: Optional[str] = None):
        """
        Re-Deploys the latest DC with the given name
        :param name: DC name
        :param namespace: Namespace
        """
        self._exec(['rollout', 'latest', name], namespace=namespace)

    def exec(self, pod_name: str, cmd: str, args: List[str], namespace: Optional[str] = None):
        proc_args = ['exec', pod_name, '--namespace', namespace, '--', cmd]
        proc_args.extend(args)
        self._exec(proc_args, print_out=True)

    def switch_context(self, context: str):
        raise NotImplemented('Not available for openshift')

    def annotate(self, name: str, key: str, value: Optional[str], namespace: Optional[str] = None):
        if value is None:
            # Remove the annotation
            self._exec(['annotate', name, key + '-'], namespace=namespace)
            return

        self._exec(['annotate', '--overwrite=true', name, key + '=' + value], namespace=namespace)

    def delete(self, name: str, namespace: str):
        try:
            self._exec(['delete', name], namespace=namespace)
        except Exception as e:
            # Yes, we all know this is bad...
            # at that point it would make much more sense to just
            # use the k8s api directly.
            if '(NotFound)' in str(e):
                return
            raise e

    def _exec(self, args, print_out: bool = False, stdin: str = None, namespace: Optional[str] = None) -> str:
        args.insert(0, self._get_bin())
        if namespace is not None:
            args.append('--namespace')
            args.append(namespace)

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
    def rollout(self, name: str, namespace: Optional[str] = None):
        self._exec(['rollout', 'restart', 'deployment', name], namespace=namespace)

    def tag(self, source: str, dest: str, namespace: Optional[str] = None):
        raise NotImplemented('Not available for k8')

    def switch_context(self, context: str):
        self._exec(['config', 'use-context', context])

    def _exec(self, args, print_out: bool = False, stdin: str = None, namespace: Optional[str] = None):
        if namespace is not None:
            args.append('--namespace')
            args.append(namespace)
        return super()._exec(args, print_out, stdin)

    def _get_bin(self) -> str:
        if platform.system() == 'Windows':
            return 'kubectl.exe'
        return 'kubectl'
