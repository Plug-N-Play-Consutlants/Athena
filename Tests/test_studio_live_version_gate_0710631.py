"""Acceptance for the Studio-to-Scout live version/root handshake."""
import io
import json
from pathlib import Path
from unittest.mock import patch

from Tools.athena_studio import AthenaStudio, PROJECT_ROOT


class Response:
    def __init__(self, value):
        self.value = value
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self):
        return json.dumps(self.value).encode()


def status(data):
    studio = object.__new__(AthenaStudio)
    with patch('Tools.athena_studio.urllib.request.urlopen', return_value=Response(data)):
        return studio._scout_runtime_status()


def test_matching_root_and_version_pass():
    d = {'app':'Scout', 'version':'v0.7.10.63.2', 'project_root':str(PROJECT_ROOT)}
    assert status(d)['ok'] is True


def test_old_runtime_rejected_even_when_port_open():
    d = {'app':'Scout', 'version':'v0.7.10.60.0', 'project_root':str(PROJECT_ROOT)}
    out = status(d)
    assert out['ok'] is False and out['actual'] == 'v0.7.10.60.0'


def test_other_repo_rejected_even_when_version_matches():
    d = {'app':'Scout', 'version':'v0.7.10.63.2', 'project_root':str(Path(PROJECT_ROOT).parent/'some-other-repo')}
    assert status(d)['ok'] is False


def test_unknown_listener_rejected():
    assert status({'app':'AnotherWebServer'})['ok'] is False


def test_stop_script_does_not_claim_an_unidentified_listener():
    from Scout import stop_scout_windows as stop
    with patch('Scout.stop_scout_windows.urllib.request.urlopen', side_effect=OSError('not Scout')):
        accepted, why = stop.is_our_scout(8765)
    assert not accepted and 'Unable to verify' in why
