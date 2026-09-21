from src.cme_radar import build_radar, score_contract, CONTRACTS


def item(title, score=90, direction="BULLISH", categories=None):
    return {
        "title": title,
        "summary": "",
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
