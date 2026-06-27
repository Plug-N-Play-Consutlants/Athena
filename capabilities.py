"""Compatibility shim for legacy root-level imports.

Canonical implementation lives in :mod:`Athena.capabilities`.
This file intentionally contains no business logic so root/module drift cannot
create duplicate capability pathways.
"""
from Athena.capabilities import *  # noqa: F401,F403
