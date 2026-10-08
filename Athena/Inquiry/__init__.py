"""Shared inquiry contracts used by professional and fantasy intelligence paths."""
from .state import InquiryState, TemporalScope, build_inquiry_state, select_primary_player_subject

__all__ = ["InquiryState", "TemporalScope", "build_inquiry_state", "select_primary_player_subject"]
