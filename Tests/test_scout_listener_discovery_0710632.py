"""Regression: old Scout on 8765 must not be invisible to the stop helper."""
from unittest.mock import patch, Mock
from Scout import stop_scout_windows as mod


def test_parse_ipv4_and_ipv6_scout_listener():
    rows = """
 TCP    127.0.0.1:8765  0.0.0.0:0  LISTENING  1234
 TCP    [::1]:8765  [::]:0  LISTENING  5678
 TCP    127.0.0.1:8765  127.0.0.1:62000  ESTABLISHED  9012
 TCP    [::1]:9000   [::]:0  LISTENING  1000
"""
    assert mod._parse_netstat_listeners(rows) == {8765: {"1234", "5678"}}


def test_netstat_no_protocol_filter_catches_ipv6():
    sample = " TCP [::1]:8765 [::]:0 LISTENING 41696\n"
    with patch.object(mod.subprocess, 'run', return_value=Mock(stdout=sample)) as run:
        assert mod.find_listening_pids() == {8765: {'41696'}}
        assert run.call_args.args[0] == ['netstat', '-ano']


def test_no_false_success_when_listener_exists_without_pid():
    class R:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return b'{"app":"Scout"}'
    with patch.object(mod.os, 'name', 'nt'), patch.object(mod, 'find_listening_pids', return_value={}), patch.object(mod.urllib.request,'urlopen',return_value=R()):
        assert mod.main() == 2
