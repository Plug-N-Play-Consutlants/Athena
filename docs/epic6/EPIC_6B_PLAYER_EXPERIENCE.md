# Epic 6B — Player Experience Foundation

Version: `0.6.2.0.0`

## Purpose

Epic 6B adds the first complete Experience Layer implementation: a structured player profile experience that Scout can render as a professional sports intelligence surface rather than a prose-only answer.

## Player Header Contract

The player identity header now carries:

- photo URL
- full name
- jersey/player number
- team
- position
- status
- deterministic assessment badges
- current-season stat boxes

Jersey/player number is a first-class field, not embedded prose.

## Tabs

### Analysis

Default executive briefing tab:

- Executive Summary
- Playing Style
- Current Season
- Career Trend
- Organizational Impact
- Risk Factors
- Future Outlook
- Confidence

### Stats

Story-first statistics tab:

- Athena Insight
- Trend Summary
- Current Assessment
- season statistics placeholder
- career statistics placeholder

## Salary / Cap Note

Salary, cap hit, contract term, retained salary, buyout implications, clauses, LTIR, and fantasy contract status should be handled through a later Contract & Cap Intelligence slice. The Player Experience identity model now includes a contract display field, but this sprint intentionally does not add cap retrieval or cap reasoning.
