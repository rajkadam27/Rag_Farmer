"""
Mandi Arbitrage RAG Utility - Cross-reference live prices with historical trends.
"""
from utils.embeddings import embed_text
from utils.chroma import mandi_trends_collection, query_collection
from utils.mandi import get_mandi_prices
from utils.llm import get_gemini_response

LANG_MAP = {
    "Marathi": "Marathi (मराठी)",
    "Hindi": "Hindi (हिंदी)",
    "English": "English",
}

ARBITRAGE_PROMPT = """You are an expert agricultural commodities analyst for Maharashtra, India.
You have access to LIVE market prices and 5 YEARS of historical price data.

Your job is to provide actionable arbitrage and timing advice to farmers:
- Compare current prices to historical averages
- Identify if prices are above or below seasonal norms
- Recommend specific actions: SELL NOW, HOLD for X days, or TRANSPORT to a better APMC
- Quote specific price differences between markets
"""


def get_arbitrage_analysis(commodity: str, state: str = "Maharashtra", lang: str = "English") -> dict:
    """
    Fetch live prices + retrieve historical trends + generate arbitrage advisory.
    """
    mapped_lang = LANG_MAP.get(lang, "English")

    # 1. Get LIVE prices
    live_data = get_mandi_prices(commodity, state, "English")
    live_prices = live_data.get("prices", [])

    # 2. Retrieve historical trends from vector DB
    trend_query = f"Historical price trends and seasonal patterns for {commodity} in Maharashtra APMCs"
    query_embedding = embed_text(trend_query).tolist()
    trend_results = query_collection(mandi_trends_collection, query_embedding, n_results=8)

    trend_docs = trend_results.get("documents", [[]])[0]
    trend_metas = trend_results.get("metadatas", [[]])[0]

    historical_context = "\n".join(trend_docs) if trend_docs else "No historical data available."

    # 3. Build arbitrage prompt
    prompt = f"""RESPOND ENTIRELY IN {mapped_lang}.

=== LIVE MARKET PRICES (TODAY) ===
Commodity: {commodity}
State: {state}
Live APMC Data: {str(live_prices)}

=== HISTORICAL TREND DATA (5 YEARS) ===
{historical_context}

=== YOUR ANALYSIS ===
Provide a comprehensive arbitrage advisory for a farmer holding {commodity}:

## 📊 Current Market Snapshot
[Today's prices across APMCs - which market is paying the most?]

## 📈 Historical Comparison
[How do today's prices compare to 5-year historical averages? Is this above/below normal for this time of year?]

## 🏆 Best Market to Sell
[Which specific APMC offers the highest price? By how much compared to the lowest?]

## ⏱️ Hold or Sell Recommendation
[Based on seasonal patterns, should the farmer sell now or hold? For how many days/weeks?]

## 🚛 Transport Advisory
[If the best price is at a distant APMC, is the price difference worth the transport cost? Assume transport cost of Rs.50-100 per quintal per 100km.]

## 🔮 Price Forecast (Next 30 Days)
[Based on historical seasonal patterns, where are prices likely headed?]

Be specific with numbers. Quote exact price differences. Give a clear, actionable recommendation.
"""

    analysis = get_gemini_response(prompt, system_instruction=ARBITRAGE_PROMPT)

    # Extract best/worst APMCs from live data for UI cards
    best_apmc = None
    worst_apmc = None
    if live_prices:
        sorted_prices = sorted(live_prices, key=lambda x: float(x.get("modal_price", 0) or 0), reverse=True)
        if sorted_prices:
            best_apmc = sorted_prices[0]
            worst_apmc = sorted_prices[-1]

    return {
        "commodity": commodity,
        "live_prices": live_prices,
        "analysis": analysis,
        "best_market": best_apmc,
        "worst_market": worst_apmc,
        "historical_sources": [
            {"commodity": m.get("commodity", ""), "year": m.get("year", ""),
             "apmc": m.get("apmc", ""), "peak_month": m.get("peak_month", ""),
             "peak_price": m.get("peak_price", "")}
            for m in trend_metas
        ],
        "source": live_data.get("source", "unknown"),
    }
