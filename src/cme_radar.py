"""Rule-based CME futures news radar for the Telegram premarket feed.

Maps ranked news catalysts to major liquid CME Group futures. Contract bias is
kept separate from NQ/SPX news pressure and is never a price forecast.
"""

from collections import defaultdict
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Contract:
    symbol: str
    name: str
    group: str
    keywords: tuple[str, ...]
    base: int = 20


GROUPS = (
    "EQUITY INDEX", "INTEREST RATES", "FX", "ENERGY",
    "METALS", "AGRICULTURE", "CRYPTO",
)

CONTRACTS = [
    Contract("ES", "E-mini S&P 500", "EQUITY INDEX", ("s&p", "s&p 500", "spx", "stocks", "equities", "wall street", "us stocks", "index futures", "risk-on", "risk-off"), 38),
    Contract("NQ", "E-mini Nasdaq-100", "EQUITY INDEX", ("nasdaq", "nasdaq-100", "nvidia", "nvda", "apple", "microsoft", "amazon", "meta", "amd", "broadcom", "ai", "semiconductor", "fed", "yields", "rates"), 40),
    Contract("RTY", "E-mini Russell 2000", "EQUITY INDEX", ("russell", "small caps", "small-cap", "regional banks", "domestic stocks", "rates", "fed"), 34),
    Contract("YM", "E-mini Dow", "EQUITY INDEX", ("dow", "industrial", "industrials", "us stocks", "equities", "stocks"), 32),
    Contract("NKD", "Nikkei 225", "EQUITY INDEX", ("nikkei", "japan stocks", "japanese stocks", "boj", "bank of japan", "yen"), 28),
    Contract("6A", "Australian Dollar", "FX", ("australia", "australian", "rba", "aud", "china", "iron ore", "commodities"), 22),
    Contract("6C", "Canadian Dollar", "FX", ("canada", "canadian", "boc", "bank of canada", "cad", "oil", "crude"), 22),
    Contract("6E", "Euro FX", "FX", ("euro", "eur", "ecb", "eurozone", "europe", "germany", "france", "italy", "european"), 24),
    Contract("6J", "Japanese Yen", "FX", ("yen", "jpy", "japan", "boj", "bank of japan", "japanese", "jgb"), 24),
    Contract("6B", "British Pound", "FX", ("pound", "sterling", "gbp", "bank of england", "boe", "uk", "britain", "british"), 21),
    Contract("6S", "Swiss Franc", "FX", ("swiss", "switzerland", "snb", "franc", "chf"), 19),
    Contract("6N", "New Zealand Dollar", "FX", ("new zealand", "rbnz", "nzd", "kiwi"), 17),
    Contract("SR3", "3-Month SOFR", "INTEREST RATES", ("fed", "federal reserve", "fomc", "interest rate", "rates", "cpi", "inflation", "pce", "jobs", "payroll", "unemployment", "sofr"), 45),
    Contract("ZT", "2-Year Treasury Note", "INTEREST RATES", ("fed", "federal reserve", "fomc", "interest rate", "rates", "cpi", "inflation", "pce", "jobs", "payroll", "unemployment", "2-year", "2 year", "treasury", "yield"), 44),
    Contract("ZF", "5-Year Treasury Note", "INTEREST RATES", ("fed", "federal reserve", "fomc", "interest rate", "rates", "cpi", "inflation", "pce", "jobs", "payroll", "treasury", "yield", "5-year", "5 year"), 42),
    Contract("ZN", "10-Year Treasury Note", "INTEREST RATES", ("fed", "federal reserve", "fomc", "interest rate", "rates", "cpi", "inflation", "pce", "jobs", "payroll", "treasury", "yield", "10-year", "10 year"), 44),
    Contract("ZB", "30-Year Treasury Bond", "INTEREST RATES", ("fed", "federal reserve", "fomc", "interest rate", "rates", "cpi", "inflation", "pce", "jobs", "payroll", "treasury", "yield", "30-year", "30 year", "bond"), 40),
    Contract("CL", "WTI Crude Oil", "ENERGY", ("oil", "crude", "wti", "brent", "opec", "opec+", "iran", "israel", "middle east", "hormuz", "supply", "inventory", "eia"), 42),
    Contract("NG", "Henry Hub Natural Gas", "ENERGY", ("natural gas", "lng", "henry hub", "gas storage", "weather", "hurricane", "pipeline"), 36),
    Contract("RB", "RBOB Gasoline", "ENERGY", ("gasoline", "rbob", "refinery", "refineries", "crack spread", "oil", "crude", "supply", "eia", "opec"), 29),
    Contract("HO", "Heating Oil", "ENERGY", ("heating oil", "diesel", "distillate", "refinery", "oil", "crude", "supply", "eia", "opec"), 27),
    Contract("GC", "Gold", "METALS", ("gold", "precious metals", "fed", "rates", "real yields", "treasury", "yield", "dollar", "usd", "geopolitics", "iran", "war"), 40),
    Contract("SI", "Silver", "METALS", ("silver", "precious metals", "gold", "fed", "rates", "dollar", "usd", "industrial demand"), 34),
    Contract("HG", "Copper", "METALS", ("copper", "china", "pboc", "manufacturing", "industrial", "construction", "stimulus", "tariff", "trade", "dollar"), 35),
    Contract("PL", "Platinum", "METALS", ("platinum", "precious metals", "auto", "automotive", "south africa", "china", "dollar"), 23),
    Contract("ZC", "Corn", "AGRICULTURE", ("corn", "maize", "usda", "crop", "harvest", "planting", "weather", "drought", "exports", "ethanol"), 36),
    Contract("ZS", "Soybeans", "AGRICULTURE", ("soybean", "soybeans", "usda", "crop", "harvest", "planting", "weather", "drought", "exports", "china", "brazil", "argentina"), 35),
    Contract("ZW", "Chicago SRW Wheat", "AGRICULTURE", ("wheat", "usda", "crop", "harvest", "planting", "weather", "drought", "exports", "russia", "ukraine", "black sea"), 35),
    Contract("LE", "Live Cattle", "AGRICULTURE", ("cattle", "beef", "livestock", "usda", "feedlot", "slaughter"), 23),
    Contract("HE", "Lean Hogs", "AGRICULTURE", ("hogs", "pork", "livestock", "usda", "china"), 20),
    Contract("BTC", "Bitcoin", "CRYPTO", ("bitcoin", "btc", "crypto", "digital assets", "sec", "etf", "ethereum", "risk-on", "risk-off", "dollar", "rates"), 34),
    Contract("ETH", "Ether", "CRYPTO", ("ether", "ethereum", "eth", "crypto", "digital assets", "sec", "etf", "bitcoin", "rates", "dollar"), 29),
]


def _parts(item):
    title = str(item.get("title", ""))
    summary = str(item.get("summary", ""))
    categories = " ".join(item.get("categories", []) or [])
    return title.lower(), summary.lower(), categories.lower(), f"{title} {summary} {categories}".lower()


def _text(item):
    title, summary, categories, text = _parts(item)
    return title, text


def _has(text, *terms):
    return any(term in text for term in terms)


def _direction(item, contract: Contract):
    """Infer direction for a specific contract; never blindly copy headline direction."""
    raw = str(item.get("direction", "NEUTRAL") or "NEUTRAL").upper()
    title, summary, categories, text = _parts(item)

    if contract.group == "INTEREST RATES":
        if _has(title, "yields retreat", "yield retreat", "yields ease", "yield eases", "lower yields", "yields fall", "yield falls", "yield decline", "yields decline", "yield drop", "yields drop", "yield slips", "yields slip"):
            return "BULLISH PRESSURE"
        if _has(title, "higher yields", "yield rises", "yields rise", "yield jumps", "yields jump", "yield climbs", "yields climb", "yield increases", "yields increase"):
            return "BEARISH PRESSURE"
        if _has(text, "lower yields", "yields retreat", "yields ease", "yields fall", "yields decline", "yields drop", "yields slip"):
            return "BULLISH PRESSURE"
        if _has(text, "higher yields", "yields rise", "yields jump", "yields climb", "yields increase"):
            return "BEARISH PRESSURE"

    if contract.group == "EQUITY INDEX":
        if _has(title, "higher yields", "yields rise", "yields jump", "yields climb", "yields increase", "rate hike", "hawkish") and (_has(title, "fall", "falls", "drop", "drops", "retreat", "retreats", "selloff", "sell-off", "slump", "loss", "losses", "lower") or _has(text, "equity futures fall", "stocks fall", "stocks drop", "equities fall")):
            return "BEARISH PRESSURE"
        if _has(title, "lower yields", "yields retreat", "yields ease", "yields fall", "yields decline", "yields drop", "rate cut", "dovish") and (_has(title, "higher", "gain", "gains", "rise", "rally", "rallies", "recover", "recovery", "rebound") or _has(text, "wall street rallies", "stocks recover", "equities recover")):
            return "BULLISH PRESSURE"
        if _has(title, "ends sharply higher", "ends higher", "stocks recover", "equities recover", "stock gains", "stocks gain", "stocks rise", "stocks rally", "stocks rebound", "equities rally", "equities rebound", "rallies", "rally", "gains", "gain", "higher", "optimism", "recovery", "recover"):
            return "BULLISH PRESSURE"
        if _has(title, "ends sharply lower", "ends lower", "stocks fall", "stocks drop", "equities fall", "equities drop", "stocks retreat", "equities retreat", "selloff", "sell-off", "losses", "slump", "falls", "drops", "lower", "loss"):
            return "BEARISH PRESSURE"
        if _has(text, "lower yields", "yields retreat", "yields ease", "rate cut", "dovish"):
            return "BULLISH PRESSURE"
        if _has(text, "higher yields", "yields rise", "yields jump", "rate hike", "hawkish"):
            return "BEARISH PRESSURE"

    if contract.symbol == "CL":
        if _has(title, "oil prices rise", "oil prices gain", "oil rises", "oil gains", "oil jumps", "oil surges", "crude rises", "crude gains", "crude jumps", "crude surges", "oil rallies", "crude rallies", "supply disruption", "supply cut", "opec cut", "production cut"):
            return "BULLISH PRESSURE"
        if _has(title, "oil prices ease", "oil prices retreat", "oil eases", "oil retreats", "oil falls", "oil drops", "oil slips", "crude falls", "crude drops", "crude eases", "crude retreats", "demand weakens") or _has(text, "oil prices ease", "oil eases", "oil falls", "crude falls", "crude drops", "demand weakens"):
            return "BEARISH PRESSURE"

    if contract.symbol in {"RB", "HO"}:
        if _has(title, "gasoline rises", "gasoline gains", "gasoline jumps", "refinery outage", "refinery shutdown"):
            return "BULLISH PRESSURE"
        if _has(title, "oil prices ease", "oil eases", "oil falls", "crude falls", "crude drops"):
            return "BEARISH PRESSURE"

    if contract.group == "METALS":
        if _has(title, "lower yields", "yields retreat", "yields ease", "dollar falls", "dollar weakens", "usd falls"):
            return "BULLISH PRESSURE"
        if _has(title, "higher yields", "yields rise", "yields jump", "dollar rises", "dollar strengthens", "usd rises"):
            return "BEARISH PRESSURE"

    if contract.group == "FX":
        if contract.symbol == "6J" and _has(title, "yen intervention", "intervention watch", "intervention risk"):
            return "MIXED"
        if contract.symbol == "6E":
            if _has(title, "euro rises", "euro gains", "euro strengthens", "euro climbs"):
                return "BULLISH PRESSURE"
            if _has(title, "euro falls", "euro drops", "euro weakens", "euro slips"):
                return "BEARISH PRESSURE"
        if contract.symbol == "6C":
            if _has(title, "oil rises", "oil jumps", "crude rises"):
                return "BULLISH PRESSURE"
            if _has(title, "oil falls", "oil drops", "crude falls", "oil eases"):
                return "BEARISH PRESSURE"
        if contract.symbol == "NKD":
            if _has(title, "nikkei rises", "nikkei gains", "japan stocks rise", "japanese stocks rise"):
                return "BULLISH PRESSURE"
            if _has(title, "nikkei falls", "nikkei drops", "japan stocks fall", "japanese stocks fall"):
                return "BEARISH PRESSURE"

    if raw in {"BULLISH", "BEARISH", "MIXED"}:
        return {"BULLISH": "BULLISH PRESSURE", "BEARISH": "BEARISH PRESSURE", "MIXED": "MIXED"}[raw]
    return "NEUTRAL"


def _contract_bias_label(direction):
    """Render CME direction explicitly as contract bias, never NQ/SPX pressure."""
    return {
        "BULLISH PRESSURE": "BULLISH CONTRACT BIAS",
        "BEARISH PRESSURE": "BEARISH CONTRACT BIAS",
        "MIXED": "MIXED CONTRACT BIAS",
    }.get(direction, "NO MATERIAL CONTRACT MAPPING")


def enrich_test_directions(items):
    """Improve Telegram headline-level equity direction labels."""
    for item in items:
        title = str(item.get("title", "")).lower()
        current = str(item.get("direction", "NEUTRAL") or "NEUTRAL").upper()
        if _has(title, "ends sharply higher", "ends higher", "stocks recover", "equities recover", "stock gains", "stocks gain", "stocks rise", "stocks rally", "stocks rebound", "equities rally", "equities rebound", "rallies", "rally"):
            item["direction"] = "BULLISH"
        elif _has(title, "ends sharply lower", "ends lower", "stocks fall", "stocks drop", "equities fall", "equities drop", "stocks retreat", "equities retreat", "selloff", "sell-off", "losses", "slump"):
            item["direction"] = "BEARISH"
        elif current == "NEUTRAL":
            if _has(title, "higher", "gains", "gain", "rises", "rally", "recover", "rebound"):
                item["direction"] = "BULLISH"
            elif _has(title, "lower", "falls", "drops", "retreats", "slips", "slump", "losses"):
                item["direction"] = "BEARISH"
    return items


def catalyst_strength(item):
    return max(0, min(100, int(item.get("score", 0) or 0)))


def _event_terms(text):
    return (
        "cpi", "pce", "payroll", "fomc", "rate decision", "opec", "usda",
        "inventory", "inventories", "production", "supply disruption", "intervention",
        "tariff", "sanctions", "earnings", "guidance", "shutdown", "refinery",
        "storage", "weather warning", "drought", "harvest", "export ban", "ceasefire",
    )


def _contract_link_is_material(contract: Contract, title_hits, content_hits, categories):
    """Require a genuine contract-specific link; category labels alone are not enough."""
    title_or_content = {h.lower() for h in (title_hits + content_hits)}
    category_hits = {h.lower() for h in categories}

    broad_equity = {"stocks", "equities", "us stocks", "wall street", "index futures", "risk-on", "risk-off"}
    if contract.symbol == "YM":
        return bool(title_or_content & {"dow", "industrial", "industrials"})
    if contract.symbol == "RTY":
        return bool(title_or_content & {"russell", "small caps", "small-cap", "regional banks", "domestic stocks"})
    if contract.symbol == "NKD":
        return bool(title_or_content & {"nikkei", "japan stocks", "japanese stocks", "boj", "bank of japan", "yen"})
    if contract.symbol == "NQ":
        return bool(title_or_content & set(contract.keywords)) or bool(title_or_content & broad_equity)
    if contract.symbol == "ES":
        return bool(title_or_content & set(contract.keywords))
    if contract.group == "FX":
        return bool(title_or_content & set(contract.keywords))
    if contract.group == "INTEREST RATES":
        rate_terms = {"fed", "federal reserve", "fomc", "interest rate", "rates", "cpi", "inflation", "pce", "jobs", "payroll", "unemployment", "sofr", "treasury", "yield", "2-year", "2 year", "5-year", "5 year", "10-year", "10 year", "30-year", "30 year", "bond"}
        return bool(title_or_content & rate_terms)
    if contract.symbol == "CL":
        return bool(title_or_content & {"oil", "crude", "wti", "brent", "opec", "opec+", "iran", "israel", "middle east", "hormuz", "supply", "inventory", "eia"})
    if contract.symbol in {"RB", "HO"}:
        return bool(title_or_content & set(contract.keywords))
    if contract.symbol == "NG":
        return bool(title_or_content & {"natural gas", "lng", "henry hub", "gas storage", "hurricane", "pipeline"})
    if contract.symbol == "HG":
        direct = {"copper", "manufacturing", "industrial", "construction", "stimulus", "pboc"}
        trade_pair = {"china", "tariff", "trade"}
        return bool(title_or_content & direct) or len(title_or_content & trade_pair) >= 2
    if contract.symbol in {"GC", "SI", "PL"}:
        return bool(title_or_content & set(contract.keywords))
    if contract.group == "AGRICULTURE":
        return bool(title_or_content & set(contract.keywords))
    if contract.group == "CRYPTO":
        return bool(title_or_content & set(contract.keywords))
    return bool(title_or_content & set(contract.keywords))


def score_contract(item, contract: Contract):
    title, summary, categories, text = _parts(item)
    normalized_title = re.sub(r"[^a-z0-9$+\- ]+", " ", title)
    normalized_summary = re.sub(r"[^a-z0-9$+\- ]+", " ", summary)
    title_hits = [k for k in contract.keywords if k.lower() in normalized_title]
    content_hits = [k for k in contract.keywords if k.lower() in f"{normalized_title} {normalized_summary}"]
    all_hits = [k for k in contract.keywords if k.lower() in text]
    if not all_hits or not _contract_link_is_material(contract, title_hits, content_hits, categories):
        return 0, 0, []

    generic_only = {"stocks", "equities", "us stocks", "oil", "crude", "rates", "dollar", "china", "weather"}
    specific_hits = [k for k in content_hits if k.lower() not in generic_only]

    if contract.symbol == "CL":
        oil_specific = {"wti", "brent", "opec", "opec+", "iran", "israel", "middle east", "hormuz", "supply", "inventory", "eia"}
        if not any(k.lower() in oil_specific for k in content_hits) and not _has(title, "oil prices ease", "oil prices rise", "oil prices gain", "oil prices fall", "oil prices drop", "oil prices retreat"):
            return 0, 0, []

    if contract.symbol == "NG" and not any(k.lower() in {"natural gas", "lng", "henry hub", "gas storage", "hurricane", "pipeline"} for k in content_hits):
        return 0, 0, []

    catalyst_score = int(item.get("score", 0) or 0)
    title_bonus = min(18, len(title_hits) * 9)
    specific_bonus = min(16, len(specific_hits) * 5)
    relevance = min(100, contract.base + title_bonus + specific_bonus + max(0, catalyst_score - 55) // 6)
    event_bonus = 10 if any(term in text for term in _event_terms(text)) else 4 if specific_hits else 0
    move_potential = min(100, max(0, relevance + event_bonus))
    strength = catalyst_strength(item)
    move_potential = min(move_potential, max(35, strength + 10))
    return relevance, move_potential, all_hits[:6]


def build_radar(items, limit=15):
    rows = []
    for item in items:
        for contract in CONTRACTS:
            impact, move_potential, hits = score_contract(item, contract)
            if impact < 50:
                continue
            direction = _direction(item, contract)
            rows.append({
                "symbol": contract.symbol,
                "name": contract.name,
                "group": contract.group,
                "impact": impact,
                "move_potential": move_potential,
                "volatility": move_potential,
                "catalyst_strength": catalyst_strength(item),
                "direction": direction,
                "title": item.get("title", ""),
                "catalyst_score": int(item.get("score", 0) or 0),
                "hits": hits,
            })

    best = {}
    for row in rows:
        old = best.get(row["symbol"])
        key = (row["move_potential"], row["impact"], row["catalyst_strength"], row["catalyst_score"])
        old_key = (-1, -1, -1, -1) if old is None else (old["move_potential"], old["impact"], old["catalyst_strength"], old["catalyst_score"])
        if old is None or key > old_key:
            best[row["symbol"]] = row
    return sorted(best.values(), key=lambda r: (r["move_potential"], r["impact"]), reverse=True)[:limit]


def _group_by_catalyst(rows):
    groups = defaultdict(list)
    for row in rows:
        key = re.sub(r"\s+", " ", str(row["title"]).strip().lower())
        groups[key].append(row)
    return sorted(groups.values(), key=lambda rs: max(r["move_potential"] for r in rs), reverse=True)


def volatility_watch(rows, limit=5):
    seen = {}
    for row in rows:
        old = seen.get(row["symbol"])
        if old is None or (row["move_potential"], row["impact"]) > (old["move_potential"], old["impact"]):
            seen[row["symbol"]] = row
    return sorted(seen.values(), key=lambda r: (r["move_potential"], r["impact"]), reverse=True)[:limit]


def format_radar(items, limit=18):
    all_material = build_radar(items, limit=len(CONTRACTS))
    rows = all_material[:limit]
    lines = ["", "━━━━━━━━━━━━━━━━━━━━", "<b>🌎 CME FUTURES RADAR — PREMARKET</b>"]
    lines.append("<i>Impact = news relevance to the contract. Move Potential = event-driven potential for elevated movement if the catalyst develops. Contract Bias = directional pressure on the named CME contract. It is not a price forecast or implied-volatility measure.</i>")
    if not rows:
        lines += ["", "No material CME futures catalysts detected in the current news set.", "<i>Rule-based mapping across major liquid CME Group benchmark futures.</i>"]
        return "\n".join(lines)

    lines += ["", "<b>🔥 VOLATILITY WATCH — MOVE POTENTIAL</b>"]
    for i, row in enumerate(volatility_watch(all_material, limit=5), 1):
        lines.append(f'{i}. <b>{row["symbol"]}</b> — {row["name"]} | Move <b>{row["move_potential"]}</b> | Impact {row["impact"]}')

    grouped = _group_by_catalyst(rows)
    for group_rows in grouped:
        title = group_rows[0]["title"]
        strength = max(r["catalyst_strength"] for r in group_rows)
        lines += ["", f"<b>⚡ CATALYST — {title}</b>", f"<i>Catalyst Strength: {strength}/100</i>"]
        group_names = sorted({r["group"] for r in group_rows}, key=lambda g: GROUPS.index(g))
        for group_name in group_names:
            lines.append(f"<b>{group_name}</b>")
            for row in sorted((r for r in group_rows if r["group"] == group_name), key=lambda r: r["move_potential"], reverse=True):
                lines.append(f'<b>{row["symbol"]}</b> — {row["name"]} | Impact <b>{row["impact"]}</b> | Move <b>{row["move_potential"]}</b> | {_contract_bias_label(row["direction"])}')

    lines += ["", "<b>📊 CME MARKET MAP — BENCHMARK FUTURES</b>"]
    by_symbol = {r["symbol"]: r for r in all_material}
    for group in GROUPS:
        lines.append(f"<b>{group}</b>")
        for contract in [c for c in CONTRACTS if c.group == group]:
            row = by_symbol.get(contract.symbol)
            if row:
                lines.append(f'<b>{contract.symbol}</b> — {contract.name} | Impact {row["impact"]} | Move {row["move_potential"]} | {_contract_bias_label(row["direction"])}')
            else:
                lines.append(f"<b>{contract.symbol}</b> — {contract.name} | — no material contract mapping")

    lines += ["", "<i>Universe focuses on major liquid CME Group benchmark futures across equity indexes, rates, FX, energy, metals, agriculture and crypto; it is not an exhaustive contract directory.</i>"]
    return "\n".join(lines)
