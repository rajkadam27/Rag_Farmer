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

