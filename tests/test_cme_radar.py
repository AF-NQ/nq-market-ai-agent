from src.cme_radar import build_radar, score_contract, CONTRACTS, format_radar


def item(title, score=90, direction="BULLISH", categories=None, summary=""):
    return {
        "title": title,
        "summary": summary,
        "score": score,
        "direction": direction,
        "categories": categories or [],
    }


def contract(symbol):
    return next(x for x in CONTRACTS if x.symbol == symbol)


def test_cpi_maps_to_rates_and_equities():
    x = item("US CPI comes in hotter than expected as Treasury yields jump", categories=["INFLATION / MACRO"])
    assert score_contract(x, contract("ZT"))[0] >= 50
    assert score_contract(x, contract("NQ"))[0] >= 50
    assert score_contract(x, contract("ZC"))[0] == 0


def test_oil_event_maps_to_energy_not_corn():
    x = item("Oil jumps after supply disruption in the Middle East", categories=["OIL / ENERGY"])
    assert score_contract(x, contract("CL"))[0] >= 50
    assert score_contract(x, contract("RB"))[0] >= 50
    assert score_contract(x, contract("ZC"))[0] == 0


def test_usda_corn_event_maps_to_agriculture():
    x = item("USDA cuts corn production forecast after drought", categories=["AGRICULTURE"])
    assert score_contract(x, contract("ZC"))[0] >= 50
    assert score_contract(x, contract("ZS"))[0] >= 50
    assert score_contract(x, contract("NQ"))[0] == 0


def test_radar_returns_distinct_contracts():
    x = item("Fed signals rates may stay higher for longer", categories=["FED / RATES"])
    rows = build_radar([x], limit=10)
    symbols = {r["symbol"] for r in rows}
    assert "ZT" in symbols
    assert "ZN" in symbols
    assert len(symbols) == len(rows)


def test_direction_is_contract_aware_for_treasuries_and_equities():
    x = item("Wall Street rallies as Treasury yields retreat", direction="NEUTRAL", categories=["TREASURIES / YIELDS"])
    rate = score_contract(x, contract("ZN"))
    equity = score_contract(x, contract("NQ"))
    assert rate[0] >= 50
    assert equity[0] >= 50

    rows = build_radar([x], limit=len(CONTRACTS))
    by_symbol = {r["symbol"]: r for r in rows}
    assert by_symbol["ZN"]["direction"] == "BULLISH PRESSURE"
    assert by_symbol["NQ"]["direction"] == "BULLISH PRESSURE"


def test_direction_inverts_for_rising_yields():
    x = item("Equity futures fall as Treasury yields jump", direction="NEUTRAL", categories=["TREASURIES / YIELDS"])
    rows = build_radar([x], limit=len(CONTRACTS))
    by_symbol = {r["symbol"]: r for r in rows}
    assert by_symbol["ZN"]["direction"] == "BEARISH PRESSURE"
    assert by_symbol["NQ"]["direction"] == "BEARISH PRESSURE"


def test_weak_global_headline_does_not_force_unrelated_contracts():
    x = item(
        'Trump pushes "super intelligence," dismisses AI risks and eyes China hotline',
        score=88,
        direction="NEUTRAL",
        categories=["INFLATION / MACRO", "CHINA / PBOC", "GEOPOLITICS"],
    )
    assert score_contract(x, contract("HG"))[0] == 0
    assert score_contract(x, contract("YM"))[0] == 0


def test_contract_bias_never_renders_neutral_bias():
    x = item("Japan intervention watch dominates markets", score=70, direction="NEUTRAL", categories=["JAPAN / BOJ"])
    report = format_radar([x])
    assert "NEUTRAL CONTRACT BIAS" not in report
    assert (
        "NO MATERIAL CONTRACT MAPPING" in report
        or "MIXED CONTRACT BIAS" in report
        or "No material CME futures catalysts detected" in report
    )


def test_market_map_uses_no_material_mapping_for_absent_contract_catalyst():
    x = item("Nasdaq rises as AI optimism lifts technology shares", score=85, direction="BULLISH", categories=["AI / SEMICONDUCTORS"])
    report = format_radar([x])
    assert "<b>NQ</b> — E-mini Nasdaq-100" in report
    assert "no material contract mapping" in report


def test_format_radar_has_event_level_strength_and_full_market_map():
    x = item("Wall Street rallies as Treasury yields retreat", direction="NEUTRAL", categories=["TREASURIES / YIELDS"])
    report = format_radar([x])
    assert "VOLATILITY WATCH — MOVE POTENTIAL" in report
    assert "Catalyst Strength:" in report
    assert "CME MARKET MAP — BENCHMARK FUTURES" in report
    assert "<b>ES</b> — E-mini S&P 500" in report
    assert "<b>CL</b> — WTI Crude Oil" in report
    assert "BULLISH CONTRACT BIAS" in report
    assert "Catalyst <b>" not in report
