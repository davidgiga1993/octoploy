import json
import platform
import subprocess
from typing import Optional, List

from oc.Model import ItemDescription, PodData


class Oc:
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

    def _exec(self, args, print_out: bool = False, stdin: str = None):
        args.insert(0, self._get_bin())
        if print_out:
            print(str(args))
        if stdin is not None:
            stdin = stdin.encode('utf-8')
        result = subprocess.run(args, capture_output=True, input=stdin)
        if result.returncode != 0:
            raise Exception('oc failed: ' + str(result.stderr.decode('utf-8')))
        output = result.stdout.decode('utf-8')
        if print_out:
            print(output)
        return output

    def _get_bin(self):
        if platform.system() == 'Windows':
            return 'oc.exe'
        return 'oc'

    def annotate(self, name: str, key: str, value: str):
        self._exec(['annotate', '--overwrite=true', name, key + '=' + value])
