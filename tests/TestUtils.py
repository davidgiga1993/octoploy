import io
import time
from typing import Optional, List
from unittest.mock import Mock

from octoploy.api.Oc import Oc

OCTOPLOY_KEY = 'key123'


class DummyCmd:
    args = []
    namespace: None
    stdin: None

    def __init__(self, args, stdin, namespace):
        self.args = args
        self.stdin = stdin
        self.namespace = namespace

    def __repr__(self):
        out = f'{self.args}'
        if self.stdin is not None:
            out += f' <- {self.stdin}'
        return out


class DummyK8sApi(Oc):
    def __init__(self):
        super().__init__()
        self.commands = []
        self.responds = []
        self._respond_not_found = False

    def not_found_by_default(self):
        self._respond_not_found = True

    def respond(self, args: List[str], stdout: '', error=None):
        self.responds.append((args, stdout, error))

    def _exec(self, args, print_out: bool = False, stdin: str = None, namespace: Optional[str] = None) -> str:
        self.commands.append(DummyCmd(args, stdin, namespace))
        for response in self.responds:
            expected_args = response[0]
            stdout = response[1]
            error = response[2]
            if expected_args == args:
                if error is not None:
                    raise error
                return stdout
        if self._respond_not_found and args[0] == 'get':
            raise Exception('NotFound')
        return '{}'


class TestHelper:
    @staticmethod
    def mock_popen_success(mock_popen, stdout=b'output', stderr=b'error', sleep_time: int = 0,
                           return_code: int = 0):
        """
        Modifies the Popen "poll" call to always return 0

        :param mock_popen: mock of Popen
        :param stdout: Std out that the process should return
        :param stderr: Std err that the process should return
        :param sleep_time: Number of seconds how long the poll() call should wait
        :param return_code: Return code of the process
        """

        stdout_stream = io.BytesIO(stdout)
        stderr_stream = io.BytesIO(stderr)

        def poll_sleep():
            if sleep_time > 0:
                time.sleep(sleep_time)
            return return_code

        process_mock = Mock()
        attrs = {'communicate.return_value': (stdout, stderr),
                 'stdout': stdout_stream,
                 'stderr': stderr_stream,
                 'poll': poll_sleep}
        process_mock.configure_mock(**attrs)
        # always return success for process execution
        mock_popen.return_value = process_mock
