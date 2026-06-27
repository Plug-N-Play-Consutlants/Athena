"""Compatibility shim for legacy root-level imports.

Canonical implementation lives in :mod:`Athena.debug_export`.
This file intentionally contains no business logic so debug export behavior has
one authoritative pathway.
"""
from Athena.debug_export import *  # noqa: F401,F403
