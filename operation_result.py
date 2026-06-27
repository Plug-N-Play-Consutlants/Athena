"""Compatibility shim for legacy root-level imports.

Canonical implementation lives in :mod:`Athena.operation_result`.
This file intentionally contains no business logic so root/module drift cannot
create duplicate Athena pathways.
"""
from Athena.operation_result import *  # noqa: F401,F403
