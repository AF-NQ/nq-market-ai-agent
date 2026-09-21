"""Rule-based CME futures news radar.

This is intentionally separate from the NQ/SPX engine. It maps the same
news catalysts to major liquid CME Group futures and estimates event impact
and volatility potential without trying to forecast price.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Contract:
    symbol: str
    name: str
    group: str
    keywords: tuple[str, ...]
    base: int = 20


CONTRACTS = [
    # Equity indexes
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
    # Interest rates
    Contract("SR3", "3-Month SOFR", "INTEREST RATES", ("fed", "federal reserve", "fomc", "interest rate", "rates", "cpi", "inflation", "pce", "jobs", "payroll", "unemployment", "sofr"), 45),
    Contract("ZT", "2-Year Treasury Note", "INTEREST RATES", ("fed", "federal reserve", "fomc", "interest rate", "rates", "cpi", "inflation", "pce", "jobs", "payroll", "unemployment", "2-year", "2 year", "treasury", "yield"), 44),
    Contract("ZF", "5-Year Treasury Note", "INTEREST RATES", ("fed", "federal reserve", "fomc", "interest rate", "rates", "cpi", "inflation", "pce", "jobs", "payroll", "treasury", "yield", "5-year", "5 year"), 42),
    Contract("ZN", "10-Year Treasury Note", "INTEREST RATES", ("fed", "federal reserve", "fomc", "interest rate", "rates", "cpi", "inflation", "pce", "jobs", "payroll", "treasury", "yield", "10-year", "10 year"), 44),
    Contract("ZB", "30-Year Treasury Bond", "INTEREST RATES", ("fed", "federal reserve", "fomc", "interest rate", "rates", "cpi", "inflation", "pce", "jobs", "payroll", "treasury", "yield", "30-year", "30 year", "bond"), 40),
    # Energy
    Contract("CL", "WTI Crude Oil", "ENERGY", ("oil", "crude", "wti", "brent", "opec", "opec+", "iran", "israel", "middle east", "hormuz", "supply", "inventory", "eia"), 42),
    Contract("NG", "Henry Hub Natural Gas", "ENERGY", ("natural gas", "lng", "henry hub", "gas storage", "weather", "hurricane", "pipeline"), 36),
    Contract("RB", "RBOB Gasoline", "ENERGY", ("gasoline", "rboB", "refinery", "refineries", "crack spread", "oil", "crude", "eia", "opec"), 29),
    Contract("HO", "Heating Oil", "ENERGY", ("heating oil", "diesel", "distillate", "refinery", "oil", "crude", "eia", "opec"), 27),
    # Metals
    Contract("GC", "Gold", "METALS", ("gold", "precious metals", "fed", "rates", "real yields", "treasury", "yield", "dollar", "usd", "geopolitics", "iran", "war"), 40),
    Contract("SI", "Silver", "METALS", ("silver", "precious metals", "gold", "fed", "rates", "dollar", "usd", "industrial demand"), 34),
    Contract("HG", "Copper", "METALS", ("copper", "china", "pboC", "pbo", "manufacturing", "industrial", "construction", "stimulus", "tariff", "trade", "dollar"), 35),
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
    return f"{item.get('title', '')} {item.get('summary', '')} {' '.join(item.get('categories', []))}".lower()


def _direction(item):
    return item.get("direction", "NEUTRAL")


def score_contract(item, contract: Contract):
    text = _text(item)
    hits = [k for k in contract.keywords if k.lower() in text]
    if not hits:
        return 0, 0, []
    catalyst = int(item.get("score", 0) or 0)
    # Diminishing returns prevent one article containing many generic terms
    # from dominating. Direct named-market terms get more weight via base.
    relevance = min(100, contract.base + min(42, len(hits) * 8) + max(0, catalyst - 55) // 5)
    if any(k in text for k in ("cpi", "pce", "payroll", "fomc", "rate decision", "opec", "usda", "inventory")):
        volatility = min(100, relevance + 8)
    elif any(k in text for k in ("fed", "oil", "crude", "inflation", "jobs", "tariff", "geopolitics", "china", "boj", "ecb")):
        volatility = min(100, relevance + 4)
    else:
        volatility = max(0, relevance - 8)
    return relevance, volatility, hits[:5]


def build_radar(items, limit=15):
    """Return top contract/event pairs; one catalyst can affect several markets."""
    rows = []
    for item in items:
        for contract in CONTRACTS:
            impact, volatility, hits = score_contract(item, contract)
            if impact < 50:
                continue
            rows.append({
                "symbol": contract.symbol,
                "name": contract.name,
                "group": contract.group,
                "impact": impact,
                "volatility": volatility,
                "direction": _direction(item),
                "title": item.get("title", ""),
                "catalyst_score": int(item.get("score", 0) or 0),
                "hits": hits,
            })
    # Keep the strongest event per contract for a clean premarket snapshot.
    best = {}
    for row in rows:
        old = best.get(row["symbol"])
        if old is None or (row["volatility"], row["impact"], row["catalyst_score"]) > (old["volatility"], old["impact"], old["catalyst_score"]):
            best[row["symbol"]] = row
    return sorted(best.values(), key=lambda r: (r["volatility"], r["impact"]), reverse=True)[:limit]


def format_radar(items, limit=15):
    rows = build_radar(items, limit=limit)
    lines = ["", "━━━━━━━━━━━━━━━━━━━━", "<b>🌎 CME FUTURES RADAR — PREMARKET</b>"]
    if not rows:
        lines.append("No material CME futures catalysts detected in the current news set.")
        lines.append("<i>Rule-based mapping; no price forecast.</i>")
        return "\n".join(lines)
    lines.append("<i>Impact = relevance of current news to the contract. Volatility = potential for elevated movement if the catalyst develops. Not a price forecast.</i>")
    current_group = None
    for row in rows:
        if row["group"] != current_group:
            current_group = row["group"]
            lines += ["", f"<b>{current_group}</b>"]
        direction = row["direction"].replace("BULLISH", "BULLISH PRESSURE").replace("BEARISH", "BEARISH PRESSURE")
        lines.append(
            f'<b>{row["symbol"]}</b> — {row["name"]} | '
            f'Impact <b>{row["impact"]}/100</b> | Volatility <b>{row["volatility"]}/100</b> | {direction}'
        )
        lines.append(f'  <i>{row["title"]}</i>')
    lines.append("<i>Universe focuses on major liquid CME Group benchmark futures across equity indexes, rates, FX, energy, metals, agriculture and crypto; it is not an exhaustive contract directory.</i>")
    return "\n".join(lines)
