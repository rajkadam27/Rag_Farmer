"""
Mandi Price Utility - Live commodity prices from AGMARKNET via data.gov.in
With AI-powered trend analysis and price prediction advice.
"""
import os
import requests
from pathlib import Path
from dotenv import load_dotenv
from utils.llm import get_gemini_response

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# Fallback sample data if API is unavailable
FALLBACK_PRICES = {
    "Cotton":    {"modal_price": 6800, "min_price": 6500, "max_price": 7100},
    "Soybean":   {"modal_price": 4100, "min_price": 3900, "max_price": 4300},
    "Onion":     {"modal_price": 1200, "min_price": 900,  "max_price": 1500},
    "Wheat":     {"modal_price": 2150, "min_price": 2050, "max_price": 2250},
    "Tur":       {"modal_price": 7200, "min_price": 6900, "max_price": 7500},
    "Sugarcane": {"modal_price": 3150, "min_price": 3000, "max_price": 3200},
    "Maize":     {"modal_price": 1800, "min_price": 1700, "max_price": 1950},
    "Gram":      {"modal_price": 5500, "min_price": 5200, "max_price": 5800},
}

LANG_MAP = {
    "Marathi": "Marathi (मराठी)",
    "Hindi":   "Hindi (हिंदी)",
    "English": "English",
}

PRICE_ADVICE_PROMPT = """You are an expert agricultural market analyst for Maharashtra, India.

IMPORTANT: RESPOND ENTIRELY AND ONLY IN {language}. DO NOT use any other language.

Analyze this mandi price data for {commodity} and give a farmer-friendly advisory:

Market Data: {price_data}

Format your response as:

**भाव मूल्यांकन / Price Assessment:** [Fair / Below MSP / Above Average / Premium]

**विकायचे की ठेवायचे? / Sell or Hold?**
[1-sentence clear recommendation with reason]

**जवळचे चांगले बाजार / Best Nearby Markets:**
[2-3 best Maharashtra markets for this crop]

**पुढील 7 दिवसांचा अंदाज / 7-Day Outlook:** [Rising / Stable / Falling — brief reason]

**MSP संदर्भ / MSP Reference:** [Official MSP if known]

Keep it concise and practical for a small farmer.
"""

def _build_ai_advice(commodity: str, prices: list, lang: str) -> str:
    """Generate AI advisory for given prices in the requested language."""
    mapped = LANG_MAP.get(lang, "English")
    prompt = PRICE_ADVICE_PROMPT.format(
        language=mapped,
        commodity=commodity,
        price_data=str(prices)
    )
    return get_gemini_response(prompt)


def get_mandi_prices(commodity: str, state: str = "Maharashtra", lang: str = "English") -> dict:
    """Fetch live mandi prices for a commodity and return AI advisory."""
    api_key = os.getenv("DATA_GOV_API_KEY", "579b464db66ec23d318f8fb8ebf70f17")

    prices = []
    source = "live"

    try:
        url = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
        params = {
            "api-key": api_key,
            "format": "json",
            "limit": 10,
            "filters[state]": state,
            "filters[commodity]": commodity,
        }
        resp = requests.get(url, params=params, timeout=8)
        data = resp.json()

        if data.get("records"):
            for record in data["records"][:5]:
                prices.append({
                    "market":      record.get("market", "N/A"),
                    "commodity":   record.get("commodity", commodity),
                    "min_price":   record.get("min_price", "N/A"),
                    "max_price":   record.get("max_price", "N/A"),
                    "modal_price": record.get("modal_price", "N/A"),
                    "date":        record.get("arrival_date", "Today"),
                })

    except Exception:
        source = "fallback"

    # Use fallback if no live data
    if not prices:
        source = "fallback"
        fb = FALLBACK_PRICES.get(commodity, {"modal_price": "N/A", "min_price": "N/A", "max_price": "N/A"})
        prices = [{
            "market":      "Nagpur APMC (Reference)",
            "commodity":   commodity,
            "min_price":   fb["min_price"],
            "max_price":   fb["max_price"],
            "modal_price": fb["modal_price"],
            "date":        "Reference (live data unavailable)",
        }]

    # Generate AI advice in requested language
    advice = _build_ai_advice(commodity, prices, lang)

    return {
        "commodity": commodity,
        "prices":    prices,
        "advice":    advice,
        "source":    source,
    }
