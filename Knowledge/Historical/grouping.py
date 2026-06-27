"""
Athena Sports Intelligence Platform

Epic 4D.3c

Historical Snapshot Grouping

Groups historical snapshots by comparable evidence type so Athena
does not compare unrelated snapshots such as production -> contract.
"""

from __future__ import annotations

from collections import defaultdict
from typing import DefaultDict

from .models import HistoricalSnapshot


def comparable_group_key(
    snapshot: HistoricalSnapshot,
) -> str:

    properties = snapshot.properties or {}

    event_type = properties.get(
        "event_type",
    )

    if event_type:
        return str(event_type)

    event_properties = properties.get(
        "event_properties",
        {},
    )

    if isinstance(event_properties, dict):

        if "season" in event_properties:
            return "seasonal"

        if (
            "contract_status" in event_properties
            or "years_remaining" in event_properties
            or "expiry_year" in event_properties
        ):
            return "contract"

        if (
            "points" in event_properties
            or "goals" in event_properties
            or "assists" in event_properties
        ):
            return "production"

    return "unknown"


def group_snapshots_by_comparable_type(
    snapshots: list[HistoricalSnapshot],
) -> dict[str, list[HistoricalSnapshot]]:

    grouped: DefaultDict[
        str,
        list[HistoricalSnapshot],
    ] = defaultdict(list)

    for snapshot in snapshots:

        grouped[
            comparable_group_key(snapshot)
        ].append(snapshot)

    return {
        key: sorted(
            items,
            key=lambda item: (
                item.captured_at,
                item.id,
            ),
        )
        for key, items in sorted(grouped.items())
    }


def comparable_pairs(
    snapshots: list[HistoricalSnapshot],
) -> list[tuple[str, HistoricalSnapshot, HistoricalSnapshot]]:

    grouped = group_snapshots_by_comparable_type(
        snapshots
    )

    pairs: list[
        tuple[
            str,
            HistoricalSnapshot,
            HistoricalSnapshot,
        ]
    ] = []

    for group_key, items in grouped.items():

        if len(items) < 2:
            continue

        for index in range(
            1,
            len(items),
        ):

            pairs.append(
                (
                    group_key,
                    items[index - 1],
                    items[index],
                )
            )

    return pairs