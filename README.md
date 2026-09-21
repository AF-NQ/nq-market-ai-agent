# NQ Market AI Agent — Free v4 (GitHub Actions Edition)

A zero-cost-by-design Telegram market-monitoring agent for NQ/Nasdaq pre-market intelligence.

## What it does

- Polls free/public news and official feeds on a 5-minute schedule.
- Gives Reuters discovery a Tier-1 reliability weight without treating Reuters as automatically infallible.
- Monitors Trump-related statements/news through free public sources and search/RSS discovery.
- Watches Fed, SEC, BLS, Treasury, White House, Nasdaq/company/earnings and broad financial news.
- Includes a free Nasdaq earnings-calendar lookup for a mega-cap watchlist where the public endpoint is available.
- Includes SEC/13F hedge-fund filing discovery; 13F is treated as a delayed holdings disclosure, not as a real-time hedge-fund P&L report.
- Deduplicates events and records them in SQLite.
- Cross-checks important events across independent sources when possible.
- Scores relevance to NQ/Nasdaq using transparent rules.
- Sends urgent high-impact events to Telegram.
- Builds a dedicated PRE-MARKET report when the New York session is ~30 minutes away.
- Runs entirely on GitHub-hosted runners; no self-hosted runner and no access to your PC/phone.
- Uses no paid API by default. AI/API adapters are optional and disabled unless you add credentials.

## Important $0 architecture note

For GitHub Free, standard GitHub-hosted runners are unlimited/free for **public repositories**. Private repositories have a monthly included-minute quota (currently 2,000 minutes on GitHub Free), which is not enough for a 5-minute schedule all month. Therefore this Free v4 is designed for a public repository with **no personal data or secrets in the repository**; Telegram credentials live only in GitHub Actions Secrets.

GitHub's scheduled workflows can be delayed or, under high load, dropped. The workflow deliberately schedules at minutes 2, 7, 12, ... rather than exactly on the hour. The application also detects the pre-market window itself. This is not an exchange-grade alerting guarantee.

## State and duplicate protection

Because GitHub-hosted runners are ephemeral, the tiny `data/state.json` file is committed back to the repository after each run. It contains only event hashes/timestamps and the last pre-open date; it contains no Telegram credentials or personal information. This lets the next runner remember what was already processed.

## Security model

- Do NOT install a self-hosted runner on your Windows PC.
- Do NOT commit `.env`, bot tokens, passwords, API keys, private keys, or personal documents.
- Store only the Telegram bot token and chat ID in GitHub Actions Secrets.
- The bot token is not a Telegram account password; it belongs to the bot.
- If a token is exposed, revoke/regenerate it in BotFather immediately.
- Repository can be public because the code contains no personal data or credentials.

## Files

```text
.github/workflows/market-monitor.yml  Scheduled 5-minute runner
.github/workflows/manual-test.yml     Manual test runner
src/                                    Python package
config.example.json                     Non-secret configuration
requirements.txt                        Python dependencies
README.md                               This guide
SECURITY.md                             Security rules
LICENSE                                 MIT license
```

## Quick start

### 1. Create Telegram bot

In Telegram open **@BotFather**, create a bot, and copy its token. Do not put the token in the code.

Send `/start` to your bot. Then obtain your chat ID using a temporary local/browser-safe method or the bot's update endpoint. Put both values into GitHub Secrets:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

### 2. Create GitHub repository

Create a new **public** repository, for example:

`nq-market-ai-agent`

Public is intentional here because GitHub Free makes standard hosted runners free/unlimited for public repositories. Never publish secrets.

### 3. Upload this archive

Upload the contents of this folder to the repository root. Keep the `.github/workflows/` directory.

### 4. Add GitHub Secrets

Repository → Settings → Secrets and variables → Actions → New repository secret.

Add:

```text
TELEGRAM_BOT_TOKEN = your bot token
TELEGRAM_CHAT_ID   = your numeric chat id
```

Optional AI providers are deliberately OFF by default. The built-in free analyzer works without them.

### 5. Enable Actions

Open the **Actions** tab. If GitHub asks to enable workflows, enable them.

Run **Manual Test** once. You should receive a Telegram message.

Then the scheduled workflow will run every 5 minutes.

## What is free and what is not

Free by design:

- GitHub public repository
- GitHub-hosted standard runner
- Python
- SQLite
- Telegram Bot API
- RSS/Atom feeds
- public official sources
- rule-based verification and NQ relevance engine

Not guaranteed free:

- paid news terminals/APIs
- OpenAI API
- Anthropic/Claude API
- premium Reuters data/API
- paid market-data APIs

This project does **not** pretend that ChatGPT/Claude API access is free. The default system uses a local deterministic analysis engine. Optional external AI adapters can be added later if you deliberately choose a provider.

## Reuters limitation

Reuters is included as a high-priority discovery source where a public RSS/search result is available. This project does not bypass paywalls, anti-bot controls, or private Reuters APIs. The bot stores headline/link metadata rather than copying full copyrighted articles.

## Pre-market logic

The application uses `America/New_York` and the exchange calendar to determine the next regular US equity open. It sends one final report when the run falls inside the configured 30–35 minute pre-open window. It also sends high-impact events outside that window immediately when detected.

The report includes:

- top new events
- source reliability and confirmation state
- NQ relevance
- macro / Fed / yields / USD / oil
- AI and semiconductors
- mega-cap / earnings
- Trump-related developments
- geopolitics
- scheduled earnings/events found from free sources
- what changed since the previous run
- links to sources

## Local test

Python 3.11+ recommended.

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python -m src.main --once
```

To test Telegram locally, set environment variables first.

## Troubleshooting

If Actions runs but Telegram is silent:

1. Check both Secrets names exactly.
2. Make sure you sent `/start` to the bot.
3. Run the Manual Test workflow.
4. Inspect the workflow log for HTTP status.

If a feed is unavailable, the collector skips it and continues. No single news source is a hard dependency.
