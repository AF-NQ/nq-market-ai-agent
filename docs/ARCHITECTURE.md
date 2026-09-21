# Architecture

## 5-minute monitor

GitHub Actions scheduled workflow → public RSS/Atom feeds → deduplication → rule-based verification → NQ relevance → SQLite state → Telegram.

## Pre-market

Every scheduled run computes the next NYSE regular open in `America/New_York`. If the run is within 30–35 minutes before open and the report has not been sent for that session, it sends the final report.

## Why no always-on server?

A free always-on VM was not reliably available. GitHub-hosted runners avoid installing anything on the user's PC. Public repositories receive free/unlimited standard runner use, while private repositories have a monthly minutes allowance.

## AI

The default Free v4 analyzer is deterministic/rule-based. This is intentional: there is no guaranteed unlimited free ChatGPT/Claude API. Optional AI adapters can be added later without changing the security model.
