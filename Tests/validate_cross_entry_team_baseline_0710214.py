"""Deliverable 1 historical divergence, now guarded by Deliverable 2 parity.

The original baseline reproduced Scout/Athena divergence in v0.7.10.2.14.
The known defect is now expected to be absent; do not assert divergence.
"""
from validate_canonical_team_ownership_0710215 import run

if __name__ == "__main__":
    run()
