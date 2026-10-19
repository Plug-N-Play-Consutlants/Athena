"""Explicitly configured, authorized HTTPS acquisition for canonical cap snapshots.

No guessed vendor endpoint, scraping, fabricated coverage, or automatic certification.
The remote publisher must supply the v0.7.10.23 canonical snapshot schema.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import ipaddress
import json
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit

from Knowledge.Contracts.cap_evidence_ingestion import CapEvidenceImport, ingest_cap_snapshot

MAX_SNAPSHOT_BYTES = 5_000_000


@dataclass(frozen=True)
class CapSnapshotSource:
    name: str
    endpoint: str
    authorized: bool = False

    def __post_init__(self) -> None:
        url = urlsplit(self.endpoint)
        if not self.name.strip() or not self.authorized:
            raise ValueError('An explicitly authorized named cap source is required')
        if url.scheme != 'https' or not url.hostname or url.username or url.password or url.fragment:
            raise ValueError('Cap source requires a credential-free HTTPS endpoint')
        try:
            address = ipaddress.ip_address(url.hostname)
        except ValueError:
            if url.hostname.lower() in ('localhost', 'localhost.localdomain') or url.hostname.endswith('.local'):
                raise ValueError('Local endpoints are not valid public cap sources')
        else:
            if not address.is_global:
                raise ValueError('Non-public IP addresses are not valid cap sources')


def acquire_cap_snapshot(source: CapSnapshotSource, *,
                         transport: Callable[..., Any] | None = None,
                         expected_team_id: str | None = None,
                         expected_as_of: str | None = None) -> CapEvidenceImport:
    """Acquire a publisher-formatted snapshot; preserve its explicit coverage claims.

    `transport` permits deterministic tests. Default requests transport blocks
    redirects, bounds response size, and sets a finite timeout. This is not a
    general web scraper or an adapter for undocumented vendor page formats.
    """
    if transport is None:
        import requests
        transport = requests.get
    response = transport(source.endpoint, timeout=15, allow_redirects=False,
                         headers={'Accept': 'application/json', 'User-Agent': 'AthenaEngine-cap-evidence/1'})
    if response.status_code != 200:
        raise ValueError(f'Cap source returned HTTP {response.status_code}')
    content = response.content
    if len(content) > MAX_SNAPSHOT_BYTES:
        raise ValueError('Cap snapshot exceeds size limit')
    try:
        payload = json.loads(content)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError('Cap source did not return valid JSON') from exc
    if not isinstance(payload, Mapping):
        raise ValueError('Cap source must return a JSON object')
    if expected_team_id is not None and payload.get('team_id') != expected_team_id:
        raise ValueError('Cap snapshot team does not match the requested team')
    if expected_as_of is not None and payload.get('as_of') != expected_as_of:
        raise ValueError('Cap snapshot date does not match the requested date')
    # Preserve publisher-provided source references. Do not upgrade provenance
    # or completeness simply because an HTTPS response succeeded.
    return ingest_cap_snapshot(payload)
