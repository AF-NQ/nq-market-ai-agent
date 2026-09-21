"""Rule-based CME futures news radar for the premarket test.

This module is intentionally separate from the NQ/SPX engine.  It maps the
same already-ranked news catalysts to major liquid CME Group futures and
estimates contract relevance, catalyst strength and move potential.  It does
not forecast price or expected volatility.
"""

from dataclasses import dataclass
from collections import defaultdict
import re


@dataclass(frozen=True)
class Contract:
    symbol: str
    name: str
    group: str
    keywords: tuple[str, ...]
    base: int = 20


GROUPS = (
    "EQUITY INDEX",
    "INTEREST RATES",
    "FX",
    "ENERGY",
    "METALS",
    "AGRICULTURE",
    "CRYPTO",
)


CONTRACTS = [
    # Equity indexes
    Contract("ES", "E-mini S&P 500", "EQUITY INDEX", ("s&p", "s&p 500", "spx", "stocks", "equities", "wall street", "us stocks", "index futures", "risk-on", "risk-off"), 38),
    Contract("NQ", "E-mini Nasdaq-100", "EQUITY INDEX", ("nasdaq", "nasdaq-100", "nvidia", "nvda", "apple", "microsoft", "amazon", "meta", "amd", "broadcom", "ai", "semiconductor", "fed", "yields", "rates"), 40),
    Contract("RTY", "E-mini Russell 2000", "EQUITY INDEX", ("russell", "small caps", "small-cap", "regional banks", "domestic stocks", "rates", "fed"), 34),
    Contract("YM", "E-mini Dow", "EQUITY INDEX", ("dow", "industrial", "industrials", "us stocks", "equities", "stocks"), 32),
    Contract("NKD", "Nikkei 225", "EQUITY INDEX", ("nikkei", "japan stocks", "japanese stocks", "boj", "bank of japan", "yen"), 28),
    # FX
    Contract("6A", "Australian Dollar", "FX", ("australia", "australian", "rba", "aud", "china", "iron ore", "commodities"), 22),
    Contract("6C", "Canadian Dollar", "FX", ("canada", "canadian", "boc", "bank of canada", "cad", "oil", "crude"), 22),
    Contract("6E", "Euro FX", "FX", ("euro", "eur", "ecb", "eurozone", "europe", "germany", "france", "italy", "european"), 24),
    Contract("6J", "Japanese Yen", "FX", ("yen", "jpy", "japan", "boj", "bank of japan", "japanese", "jgb"), 24),
    Contract("6B", "British Pound", "FX", ("pound", "sterling", "gbp", "bank of england", "boe", "uk", "britain", "british"), 21),
    Contract("6S", "Swiss Franc", "FX", ("swiss", "switzerland", "snb", "franc", "chf"), 19),
    Contract("6N", "New Zealand Dollar", "FX", ("new zealand", "rbnz", "nzd", "kiwi"), 17),
    # Interest rates
    Contract("SR3", "3-Month SOFR", "INTEREST RATES", ("fed", "federal reserve", "fomc", "interest rate", "rates", "cpi", "inflation", "pce", "jobs", "payroll", "unemployment", "sofr"), 45),
    Contract("ZT", "2-Year Treasury Note", "INTEREST RATES", ("fed", "federal reserve", "fomc", "interest rate", "rates", "cpi", "inflation", "pce", "jobs", "payroll", "unemployment", "2-year", "2 year", "treasury", "yield"), 44),
    Contract("ZF", "5-Year Treasury Note", "INTEREST RATES", ("fed", "federal reserve", "fomc", "interest rate", "rates", "cpi", "inflation", "pce", "jobs", "payroll", "treasury", "yield", "5-year", "5 year"), 42),
    Contract("ZN", "10-Year Treasury Note", "INTEREST RATES", ("fed", "federal reserve", "fomc", "interest rate", "rates", "cpi", "inflation", "pce", "jobs", "payroll", "treasury", "yield", "10-year", "10 year"), 44),
    Contract("ZB", "30-Year Treasury Bond", "INTEREST RATES", ("fed", "federal reserve", "fomc", "interest rate", "rates", "cpi", "inflation", "pce", "jobs", "payroll", "treasury", "yield", "30-year", "30 year", "bond"), 40),
    # Energy
    Contract("CL", "WTI Crude Oil", "ENERGY", ("oil", "crude", "wti", "brent", "opec", "opec+", "iran", "israel", "middle east", "hormuz", "supply", "inventory", "eia"), 42),
    Contract("NG", "Henry Hub Natural Gas", "ENERGY", ("natural gas", "lng", "henry hub", "gas storage", "weather", "hurricane", "pipeline"), 36),
    Contract("RB", "RBOB Gasoline", "ENERGY", ("gasoline", "rbob", "refinery", "refineries", "crack spread", "oil", "crude", "supply", "eia", "opec"), 29),
    Contract("HO", "Heating Oil", "ENERGY", ("heating oil", "diesel", "distillate", "refinery", "oil", "crude", "supply", "eia", "opec"), 27),
    # Metals
    Contract("GC", "Gold", "METALS", ("gold", "precious metals", "fed", "rates", "real yields", "treasury", "yield", "dollar", "usd", "geopolitics", "iran", "war"), 40),
    Contract("SI", "Silver", "METALS", ("silver", "precious metals", "gold", "fed", "rates", "dollar", "usd", "industrial demand"), 34),
    Contract("HG", "Copper", "METALS", ("copper", "china", "pboc", "manufacturing", "industrial", "construction", "stimulus", "tariff", "trade", "dollar"), 35),
    Contract("PL", "Platinum", "METALS", ("platinum", "precious metals", "auto", "automotive", "south africa", "china", "dollar"), 23),
    # Agriculture
    Contract("ZC", "Corn", "AGRICULTURE", ("corn", "maize", "usda", "crop", "harvest", "planting", "weather", "drought", "exports", "ethanol"), 36),
    Contract("ZS", "Soybeans", "AGRICULTURE", ("soybean", "soybeans", "usda", "crop", "harvest", "planting", "weather", "drought", "exports", "china", "brazil", "argentina"), 35),
    Contract("ZW", "Chicago SRW Wheat", "AGRICULTURE", ("wheat", "usda", "crop", "harvest", "planting", "weather", "drought", "exports", "russia", "ukraine", "black sea"), 35),
    Contract("LE", "Live Cattle", "AGRICULTURE", ("cattle", "beef", "livestock", "usda", "feedlot", "slaughter"), 23),
    Contract("HE", "Lean Hogs", "AGRICULTURE", ("hogs", "pork", "livestock", "usda", "china"), 20),
    # Crypto
    Contract("BTC", "Bitcoin", "CRYPTO", ("bitcoin", "btc", "crypto", "digital assets", "sec", "etf", "ethereum", "risk-on", "risk-off", "dollar", "rates"), 34),
    Contract("ETH", "Ether", "CRYPTO", ("ether", "ethereum", "eth", "crypto", "digital assets", "sec", "etf", "bitcoin", "rates", "dollar"), 29),
]


def _text(item):
    title = str(item.get("title", ""))
    summary = str(item.get("summary", ""))
    categories = " ".join(item.get("categories", []) or [])
    # Title is deliberately repeated: a title hit is stronger than a generic
    # category/summary mention and prevents context-only mentions from driving mapping.
    return title.lower(), f"{title} {summary} {categories}".lower()


def _direction(item, contract: Contract):
    direction = str(item.get("direction", "NEUTRAL") or "NEUTRAL").upper()
    if direction not in {"BULLISH", "BEARISH", "NEUTRAL"}:
        return "NEUTRAL"
    return direction.replace("BULLISH", "BULLISH PRESSURE").replace("BEARISH", "BEARISH PRESSURE")


def _catalyst_strength(item, title_hits, all_hits):
    score = int(item.get("score", 0) or 0)
    freshness = float(item.get("freshness", 0) or 0)
    source = float(item.get("source_quality", 0) or 0)
    # Strength describes the underlying news catalyst, not expected price move.
    strength = min(100, max(0, score))
    if title_hits:
        strength = min(100, strength + min(10, len(title_hits) * 4))
    if freshness:
        strength = min(100, strength + min(5, int(freshness / 20)))
    if source:
        strength = min(100, strength + min(5, int(source / 20)))
    if not all_hits:
        strength = max(0, strength - 10)
    return strength


def score_contract(item, contract: Contract):
    """Score one contract against one catalyst.

    Title matches are stronger than summary/category matches. This is the key
    guard against an article merely mentioning an unrelated market in passing.
    """
    title, text = _text(item)
    normalized_title = re.sub(r"[^a-z0-9$+\- ]+", " ", title)
    title_hits = [k for k in contract.keywords if k.lower() in normalized_title]
    all_hits = [k for k in contract.keywords if k.lower() in text]
    if not all_hits:
        return 0, 0, []

    # If there is no direct title signal, require a specific category/event
    # connection. Generic words such as stocks/equities/oil are not sufficient.
    generic_only = {"stocks", "equities", "us stocks", "oil", "crude", "rates", "dollar", "china", "weather"}
    specific_hits = [k for k in all_hits if k.lower() not in generic_only]
    if not title_hits and not specific_hits:
        return 0, 0, []

    catalyst_score = int(item.get("score", 0) or 0)
    title_bonus = min(18, len(title_hits) * 9)
    specific_bonus = min(16, len(specific_hits) * 5)
    relevance = min(100, contract.base + title_bonus + specific_bonus + max(0, catalyst_score - 55) // 6)

    event_terms = (
        "cpi", "pce", "payroll", "fomc", "rate decision", "opec", "usda",
        "inventory", "production", "supply disruption", "intervention", "tariff",
        "earnings", "guidance", "shutdown", "sanctions",
    )
    move_bonus = 10 if any(term in text for term in event_terms) else 4 if specific_hits else 0
    volatility = min(100, max(0, relevance + move_bonus))
    strength = _catalyst_strength(item, title_hits, all_hits)
    # A weak catalyst cannot create a high move-potential score merely because
    # the contract is structurally sensitive to that theme.
    volatility = min(volatility, max(35, strength + 10))
    return relevance, volatility, all_hits[:6]


def build_radar(items, limit=15):
    """Return the strongest contract/catalyst pairs, deduped by contract.

    The formatter later groups contracts by catalyst, so one event can explain
    several affected contracts without printing the same headline repeatedly.
    """
    rows = []
    for item in items:
        for contract in CONTRACTS:
            impact, move_potential, hits = score_contract(item, contract)
            if impact < 50:
                continue
            title_hits = [k for k in contract.keywords if k.lower() in str(item.get("title", "")).lower()]
            rows.append({
                "symbol": contract.symbol,
                "name": contract.name,
                "group": contract.group,
                "impact": impact,
                "move_potential": move_potential,
                "volatility": move_potential,  # compatibility for existing tests/callers
                "catalyst_strength": _catalyst_strength(item, title_hits, hits),
                "direction": _direction(item, contract),
                "title": item.get("title", ""),
                "catalyst_score": int(item.get("score", 0) or 0),
                "hits": hits,
            })

    best = {}
    for row in rows:
        old = best.get(row["symbol"])
        key = (row["catalyst_strength"], row["move_potential"], row["impact"], row["catalyst_score"])
        old_key = (-1, -1, -1, -1) if old is None else (old["catalyst_strength"], old["move_potential"], old["impact"], old["catalyst_score"])
        if old is None or key > old_key:
            best[row["symbol"]] = row
    return sorted(best.values(), key=lambda r: (r["catalyst_strength"], r["move_potential"], r["impact"]), reverse=True)[:limit]


def _group_by_catalyst(rows):
    groups = defaultdict(list)
    for row in rows:
        key = re.sub(r"\s+", " ", str(row["title"]).strip().lower())
        groups[key].append(row)
    return sorted(groups.values(), key=lambda rs: max(r["catalyst_strength"] for r in rs), reverse=True)


def format_radar(items, limit=18):
    rows = build_radar(items, limit=limit)
    lines = ["", "━━━━━━━━━━━━━━━━━━━━", "<b>🌎 CME FUTURES RADAR — PREMARKET</b>"]
    lines.append("<i>Impact = news relevance to the contract. Move Potential = potential for elevated movement if the catalyst develops. Catalyst Strength = strength/freshness/source quality of the underlying event. None is a price forecast.</i>")

    if not rows:
        lines.append("")
        lines.append("No material CME futures catalysts detected in the current news set.")
        lines.append("<i>Rule-based mapping across major liquid CME Group benchmark futures.</i>")
        return "\n".join(lines)

    grouped = _group_by_catalyst(rows)
    seen_groups = set()
    for group_rows in grouped:
        title = group_rows[0]["title"]
        group_names = sorted({r["group"] for r in group_rows}, key=lambda g: GROUPS.index(g))
        lines += ["", f"<b>⚡ CATALYST — {title}</b>"]
        for group_name in group_names:
            lines.append(f"<b>{group_name}</b>")
            for row in sorted((r for r in group_rows if r["group"] == group_name), key=lambda r: r["move_potential"], reverse=True):
                lines.append(
                    f'<b>{row["symbol"]}</b> — {row["name"]} | '
                    f'Impact <b>{row["impact"]}</b> | Move <b>{row["move_potential"]}</b> | '
                    f'Catalyst <b>{row["catalyst_strength"]}</b> | {row["direction"]}'
                )
        seen_groups.update(group_names)

    # Explicitly show coverage gaps so absence is meaningful rather than silent.
    covered = set(seen_groups)
    missing = [g for g in GROUPS if g not in covered]
    if missing:
        lines += ["", "<b>NO MATERIAL CATALYST</b>"]
        for group in missing:
            lines.append(f"• {group}")

    lines += ["", "<i>Universe focuses on major liquid CME Group benchmark futures across equity indexes, rates, FX, energy, metals, agriculture and crypto; it is not an exhaustive contract directory.</i>"]
    return "\n".join(lines)
