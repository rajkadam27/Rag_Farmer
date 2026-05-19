"""
Features Router - All new real-time AI feature endpoints.
Handles: Vision, Weather, Mandi, PDF Summarizer, Field Health, Scheme Checker, Land Health
"""
import os
import shutil
from fastapi import APIRouter, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse

router = APIRouter()

# ─── 1. AI VISION - Crop Diagnosis ────────────────────────────────────────────

@router.post("/diagnose")
async def diagnose_crop(file: UploadFile = File(...), language: str = Form("Marathi")):
    """Upload a crop photo and get AI pest/disease diagnosis in the specified language."""
    from utils.vision import diagnose_crop_image

    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are accepted.")

    temp_path = f"temp_diagnosis_{os.getpid()}.jpg"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        result = diagnose_crop_image(temp_path, language)
        return {"diagnosis": result}

    except Exception as e:
        return {"diagnosis": f"Error during diagnosis: {str(e)}"}
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


# ─── 2. WEATHER - Hyperlocal Farming Advice ───────────────────────────────────

@router.get("/weather")
async def get_weather(city: str, lang: str = "English"):
    """Fetch live weather and AI farming advice for a city in the specified language."""
    from utils.weather import get_weather_advice
    result = get_weather_advice(city, lang)
    return result


# ─── 3. MANDI - Live Commodity Prices + AI Advisory ──────────────────────────

@router.get("/mandi")
async def get_mandi(commodity: str = "Soybean", state: str = "Maharashtra", lang: str = "English"):
    """Fetch live mandi prices with AI sell/hold advice in the specified language."""
    from utils.mandi import get_mandi_prices
    result = get_mandi_prices(commodity, state, lang)
    return result


# ─── 4. PDF SUMMARIZER - Scheme Document Analysis ─────────────────────────────

@router.post("/pdf-summarize")
async def summarize_pdf(file: UploadFile = File(...), language: str = Form("Marathi")):
    """Upload a PDF (scheme document) and get an AI summary & text context in the specified language."""
    from utils.pdf_tool import summarize_pdf, extract_pdf_text

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    temp_path = f"temp_pdf_{os.getpid()}.pdf"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        summary = summarize_pdf(temp_path, language)
        context = extract_pdf_text(temp_path)
        return {"summary": summary, "context": context}

    except Exception as e:
        return {"summary": f"PDF processing error: {str(e)}", "context": ""}
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


@router.post("/pdf-chat")
async def chat_with_pdf(data: dict):
    """Ask follow-up questions about the PDF using the provided context."""
    from utils.llm import get_gemini_response
    question = data.get("question")
    context = data.get("context", "")
    language = data.get("language", "Marathi")
    
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
        
    lang_map = {
        "Marathi": "Marathi (मराठी)",
        "Hindi": "Hindi (हिंदी)",
        "English": "English"
    }
    mapped_lang = lang_map.get(language, "English")
    
    prompt = f"""You are a helpful government scheme advisor and precision agriculture consultant for Maharashtra, India.
    RESPOND ENTIRELY IN THIS LANGUAGE: {mapped_lang}
    
    Here is the text context extracted from the PDF document uploaded by the farmer:
    ---
    {context}
    ---
    
    The farmer is asking the following question about this document:
    "{question}"
    
    Please answer the farmer's question accurately, clearly, and simply based on the document context. If the answer is not specified in the document, tell them politely that the document doesn't mention it, and offer a helpful expert suggestion related to their question. Keep it concise.
    """
    response = get_gemini_response(prompt)
    return {"response": response}



# ─── 5. FIELD HEALTH - Soil & Climate via Open-Meteo (no auth needed) ─────────

@router.get("/field-health")
async def get_field_health(lat: float, lon: float, lang: str = "English"):
    """Get soil temperature, moisture, and AI field health analysis using Open-Meteo in the specified language."""
    import requests
    from utils.llm import get_gemini_response

    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&hourly=soil_temperature_0cm,soil_moisture_0_to_1cm"
            f"&daily=precipitation_sum,et0_fao_evapotranspiration,temperature_2m_max,temperature_2m_min"
            f"&timezone=Asia/Kolkata&forecast_days=3"
        )
        resp = requests.get(url, timeout=15)
        data = resp.json()

        # Extract summary data
        daily = data.get("daily", {})
        summary = {
            "location": {"lat": lat, "lon": lon},
            "max_temp": daily.get("temperature_2m_max", [None])[0],
            "min_temp": daily.get("temperature_2m_min", [None])[0],
            "rainfall_mm": daily.get("precipitation_sum", [None])[0],
            "evapotranspiration": daily.get("et0_fao_evapotranspiration", [None])[0],
        }

        hourly = data.get("hourly", {})
        if hourly.get("soil_temperature_0cm"):
            summary["soil_temp_surface"] = hourly["soil_temperature_0cm"][6]  # 7 AM reading
        if hourly.get("soil_moisture_0_to_1cm"):
            summary["soil_moisture"] = round(hourly["soil_moisture_0_to_1cm"][6] * 100, 1)

        lang_map = {
            "Marathi": "Marathi (मराठी)",
            "Hindi": "Hindi (हिंदी)",
            "English": "English"
        }
        mapped_lang = lang_map.get(lang, "English")

        # AI interpretation
        prompt = f"""You are a precision agriculture expert for Maharashtra, India.
RESPOND ENTIRELY IN THIS LANGUAGE: {mapped_lang}

Based on this field data: {summary}

Provide a brief FIELD HEALTH REPORT:
**Overall Field Status:** [Excellent / Good / Needs Attention / Critical]
**Irrigation Need:** [Urgent / Schedule Tomorrow / Not Needed / Check soil manually]
**Soil Temperature:** [Good for sowing / Too hot / Too cold for roots]
**Rainfall Forecast:** [Adequate / Insufficient / Heavy rain expected]
**Action for Today:** [One specific action the farmer should take]
"""
        ai_report = get_gemini_response(prompt)
        return {"field_data": summary, "ai_report": ai_report}

    except requests.exceptions.Timeout:
        return {"error": "Field health service timed out."}
    except Exception as e:
        return {"error": f"Field health error: {str(e)}"}


# ─── 6. SCHEME ELIGIBILITY CHECKER ───────────────────────────────────────────

@router.post("/check-eligibility")
async def check_scheme_eligibility(data: dict):
    """Check farmer eligibility for government schemes with language support."""
    from utils.scheme_checker import check_eligibility
    try:
        profile = data.get("profile", {})
        language = data.get("language", "Marathi")
        result = check_eligibility(profile, language)
        return {"result": result}
    except Exception as e:
        return {"result": f"Error checking eligibility: {str(e)}"}


# ─── 7. LAND HEALTH DASHBOARD - Historical 7-day Soil Data ───────────────────

@router.get("/land-health")
async def get_land_health(lat: float, lon: float, lang: str = "English"):
    """Get 7-day historical soil and climate data with AI land health report in the specified language."""
    from utils.land_health import get_historical_land_health
    return get_historical_land_health(lat, lon, lang)


# ─── 8. DYNAMIC SCHEMES & LIVE SOWING PLANNERS ───────────────────────────────

@router.get("/schemes")
async def get_schemes():
    """Fetch all government scheme records from local JSONL data storage."""
    import json
    from pathlib import Path
    schemes_path = Path("data/schemes/scheme_cards.jsonl")
    if not schemes_path.exists():
        return {"schemes": []}
    
    schemes = []
    try:
        with open(schemes_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    schemes.append(json.loads(line.strip()))
    except Exception as e:
        print("Error reading schemes:", e)
    return {"schemes": schemes}


@router.post("/fertilizer-advisor")
async def get_fertilizer_advisor(data: dict):
    """Generate customized AI NPK precision fertilizer schedules using Gemini."""
    from utils.llm import get_gemini_response
    crop = data.get("crop", "cotton")
    soil_type = data.get("soil_type", "Loamy")
    target_yield = data.get("target_yield", "10")
    irrigation = data.get("irrigation", "Drip")
    lang = data.get("language", "Marathi")
    
    lang_map = {
        "Marathi": "Marathi (मराठी)",
        "Hindi": "Hindi (हिंदी)",
        "English": "English"
    }
    mapped_lang = lang_map.get(lang, "English")
    
    prompt = f"""You are a precision crop nutrition expert for Maharashtra, India.
Provide a customized NPK and fertilization advisory for:
- Crop: {crop}
- Soil Type: {soil_type}
- Target Yield: {target_yield} Quintals/Acre
- Irrigation Source: {irrigation}

RESPOND ENTIRELY IN THIS LANGUAGE: {mapped_lang}

Format the response in clean, beautiful Markdown. Include these exact sections:
# 🌾 AI Fertilizer Optimization Plan

## 1. Basal Application (Sowing Time)
- [List specific fertilizers like DAP, Single Super Phosphate, Urea in kg/acre]

## 2. Top Dressing Split Schedule
- **Stage 1 (25-30 Days After Sowing):** [Fertilizers and doses]
- **Stage 2 (50-60 Days After Sowing):** [Fertilizers and doses]

## 3. Micronutrient & Foliar Recommendation
- [Specific advice for Zinc, Boron, or Iron if relevant, or standard NPK sprays]

## 4. Organic Matter & Soil Vigor Upgrades
- [FYM, Vermicompost, or Trichoderma advice]
"""
    
    advice = get_gemini_response(prompt)
    return {"advice": advice}


@router.get("/sowing-suitability")
async def get_sowing_suitability(city: str, crop: str, lang: str = "Marathi"):
    """Fetch live weather forecasts and compute sowing suitability score using Gemini."""
    import requests
    from utils.llm import get_gemini_response
    import json
    
    # Coordinate dictionary of major Maharashtra districts
    coords = {
        "pune": (18.5204, 73.8567),
        "satara": (17.6799, 74.0088),
        "nashik": (19.9975, 73.7898),
        "nagpur": (21.1458, 79.0882),
        "aurangabad": (19.8762, 75.3433),
        "solapur": (17.6599, 75.9064),
        "jalgaon": (21.0077, 75.5626),
        "amravati": (20.9374, 77.7796),
        "kolhapur": (16.7050, 74.2433),
        "nanded": (19.1383, 77.3210),
        "latur": (18.4088, 76.5604),
        "ahmednagar": (19.0948, 74.7480),
        "mumbai": (19.0760, 72.8777)
    }
    
    city_key = city.lower().strip()
    lat, lon = coords.get(city_key, (17.6799, 74.0088))
    
    forecast_summary = {}
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=Asia/Kolkata"
        resp = requests.get(url, timeout=10)
        weather_data = resp.json()
        daily = weather_data.get("daily", {})
        forecast_summary = {
            "max_temps": daily.get("temperature_2m_max", []),
            "min_temps": daily.get("temperature_2m_min", []),
            "precipitation": daily.get("precipitation_sum", [])
        }
    except Exception as e:
        forecast_summary = {"error": f"Weather API error: {str(e)}"}
        
    lang_map = {
        "Marathi": "Marathi (मराठी)",
        "Hindi": "Hindi (हिंदी)",
        "English": "English"
    }
    mapped_lang = lang_map.get(lang, "English")
    
    prompt = f"""You are a climate-smart sowing advisor for Maharashtra, India.
Evaluate the sowing readiness/suitability index (0 to 100%) for:
- Crop: {crop}
- Location: {city} (Lat: {lat}, Lon: {lon})
- 7-Day Weather Forecast: {forecast_summary}

RESPOND ENTIRELY IN THIS LANGUAGE: {mapped_lang}

You MUST output your response in JSON format ONLY, matching this schema:
{{
   "score": [an integer between 0 and 100 representing sowing readiness],
   "suitability": "[a word like Optimal, Good, Moderate, or Risky]",
   "advisory": "[detailed markdown advisory, highlighting soil conditions, precipitation fit, temperature stability]",
   "checklist": [
      "[actionable schedule item 1]",
      "[actionable schedule item 2]",
      "[actionable schedule item 3]"
   ],
   "alerts": "[weather/soil warning or alert message if any]"
}}

Ensure that the returned text is valid JSON. Do not put markdown blocks like ```json around the output, return raw JSON string.
"""
    
    try:
        resp_text = get_gemini_response(prompt).strip()
        if resp_text.startswith("```json"):
            resp_text = resp_text[7:]
        if resp_text.endswith("```"):
            resp_text = resp_text[:-3]
        resp_text = resp_text.strip()
        result = json.loads(resp_text)
    except Exception as e:
        result = {
            "score": 75,
            "suitability": "Good",
            "advisory": f"Dynamic climate advisory generated. (Fallback mode: {str(e)})",
            "checklist": ["Verify soil moisture content manually", "Proceed with seed treatment", "Monitor rains before final sowing"],
            "alerts": "No severe alerts."
        }
        
    return result


# ─── 9. GR RAG PORTAL - Government Resolution Knowledge Base ─────────────────

@router.post("/gr-query")
async def query_government_resolutions(data: dict):
    """Query the GR vector database with a farmer's natural language question."""
    from utils.gr_rag import query_gr
    question = data.get("question", "")
    lang = data.get("language", "English")

    if not question.strip():
        return {"answer": "Please enter a question.", "sources": []}

    try:
        result = query_gr(question, lang)
        return result
    except Exception as e:
        return {"answer": f"Error querying GR database: {str(e)}", "sources": []}


# ─── 10. MANDI ARBITRAGE RAG - Historical Price Intelligence ─────────────────

@router.post("/mandi-arbitrage")
async def mandi_arbitrage_analysis(data: dict):
    """Cross-reference live mandi prices with 5-year historical trends for arbitrage advice."""
    from utils.mandi_rag import get_arbitrage_analysis
    commodity = data.get("commodity", "Soybean")
    state = data.get("state", "Maharashtra")
    lang = data.get("language", "English")

    try:
        result = get_arbitrage_analysis(commodity, state, lang)
        return result
    except Exception as e:
        return {
            "commodity": commodity,
            "live_prices": [],
            "analysis": f"Error generating arbitrage analysis: {str(e)}",
            "best_market": None,
            "worst_market": None,
            "historical_sources": [],
            "source": "error",
        }
