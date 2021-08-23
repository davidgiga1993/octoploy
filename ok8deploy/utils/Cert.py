from typing import Optional, List


class Cert:
    """
    Parses pem files and extracts the cert, cacert, and key
    """

    def __init__(self, pem: str):
        self.key = None  # type: Optional[str]
        self.cert = None  # type: Optional[str]
        self.cacerts = []  # type: List[str]

        with open(pem) as f:
            lines = f.readlines()

        line_buffer = []
        mode = 0
        for line in lines:
            if '-BEGIN CERTIFICATE-' in line:
                line_buffer = [line]
                mode = 1
                continue
            if '-BEGIN PRIVATE KEY-' in line:
                line_buffer = [line]
                mode = 2
                continue
            if mode == 0:
                # Ignore
                continue

            line_buffer.append(line)
            if mode == 2 and '-END PRIVATE KEY-' in line:
                self.key = ''.join(line_buffer)
                mode = 0
                continue

            if mode == 1 and '-END CERTIFICATE-' in line:
                # End of segment
                if self.cert is None:
                    self.cert = ''.join(line_buffer)
                    continue
                self.cacerts.append(''.join(line_buffer))
                mode = 0
