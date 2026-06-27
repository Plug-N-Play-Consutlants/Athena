# Sports Intelligence Platform

## Overview

The Sports Intelligence Platform is a provider-neutral and sport-neutral platform built around a shared deterministic Sports Intelligence Engine.

The engine is responsible for acquiring, normalizing, enriching and reasoning about sports data. It produces canonical intelligence that can be consumed by multiple products without duplicating logic.

### Platform Pipeline

Fetch
→ Build
→ Knowledge
→ Intelligence
→ AI

Each layer has a single responsibility. No layer skips another.

## Products

The shared engine powers three primary products:

1. Fantasy Sports Intelligence
   - League analysis
   - Team analysis
   - Trade exploration
   - Draft preparation
   - Long-term roster planning

2. Public Sports Intelligence
   - Professional team analysis
   - Trade scenarios
   - Salary cap analysis
   - Organizational intelligence
   - Prospect pipeline analysis

3. AI Content Platform
   - Articles
   - Reports
   - Weekly summaries
   - Player and team insights

Future consumers include public APIs, web applications, desktop applications and mobile applications.

## Architecture

Providers → Build → Knowledge → Intelligence → AI

Providers contain provider-specific logic only. All downstream layers operate exclusively on canonical objects.


## Vocabulary

The repository uses standardized platform language:

- Sports Intelligence Platform: the full ecosystem.
- Sports Intelligence Engine: the deterministic shared core.
- Products: Fantasy Sports Intelligence, Public Sports Intelligence and AI Content Platform.
- Providers: external data sources.
- Consumers: APIs, applications and interfaces that use engine output.

See `docs/Platform Vocabulary.md` for the canonical terminology.
