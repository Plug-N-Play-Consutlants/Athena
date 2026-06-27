"""Canonical public-intelligence intent types for Athena PIF-1."""

from __future__ import annotations

from enum import Enum


class IntentType(str, Enum):
    """Stable intent identifiers used before evidence retrieval."""

    PLAYER_PROFILE = "player_profile"
    PLAYER_ANALYSIS = "player_analysis"
    PLAYER_COMPARISON = "player_comparison"
    TEAM_PROFILE = "team_profile"
    TEAM_ANALYSIS = "team_analysis"
    TEAM_COMPARISON = "team_comparison"
    LEAGUE_SUMMARY = "league_summary"
    TRANSACTION_SUMMARY = "transaction_summary"
    DRAFT_ANALYSIS = "draft_analysis"
    PROSPECT_ANALYSIS = "prospect_analysis"
    NEWS_SUMMARY = "news_summary"
    HISTORICAL_QUESTION = "historical_question"
    PROJECTION = "projection"
    RULEBOOK_QUESTION = "rulebook_question"
    GENERAL_DISCUSSION = "general_discussion"
    UNKNOWN = "unknown"
