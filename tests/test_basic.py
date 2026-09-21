from src.verify import relevance

def test_relevance():
    s,l,r=relevance({"title":"Fed rate decision and Nasdaq futures","source":"Reuters Markets","summary":"","link":"x"})
    assert l == "HIGH"
    assert s > 0
