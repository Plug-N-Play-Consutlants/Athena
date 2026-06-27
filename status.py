"""Compatibility shim for legacy root-level imports.

Canonical implementation lives in :mod:`Athena.status`.
This file intentionally contains no business logic so root/module drift cannot
create duplicate Athena pathways.
"""
from Athena.status import *  # noqa: F401,F403
