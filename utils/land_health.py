"""
Land Health Utility - Historical soil & climate data from Open-Meteo
Provides multi-day soil health trend data for NDVI-like field assessment.
No API key required.
"""
import requests
from utils.llm import get_gemini_response

LAND_HEALTH_PROMPT = """You are a soil scientist and precision agriculture expert for Maharashtra, India.
Based on the soil and climate data for this farm location over the past 7 days, generate a SOIL HEALTH CARD.

RESPOND ENTIRELY IN THIS LANGUAGE: {language}

Location: Lat {lat}, Lon {lon}
Historical 7-Day Data:
{data}

Generate a FIELD HEALTH CARD in this format:

**🌱 SOIL HEALTH SCORE: [X/100]**
(Based on moisture, temperature, and rainfall balance)

**Soil Condition: [Excellent / Good / Fair / Poor]**

**📊 Key Indicators:**
- Soil Moisture: [Low/Adequate/High] - [what it means for crops]
- Surface Temperature: [Normal/Hot/Cool] - [effect on root growth]
- Rainfall Balance: [Surplus/Adequate/Deficit] - [irrigation recommendation]
- Evapotranspiration: [High/Normal/Low] - [water stress level]

**🌾 Current Season Suitability:**
[Which crops are most suitable right now based on this data]

**⚠️ Alerts:**
[Any soil health concerns that need immediate attention]

**💧 Irrigation Recommendation:**
[Specific advice - how many hours/days gap before next irrigation]

**🔬 Long-term Soil Health Tips:**
1. [Tip 1 - specific to this data]
2. [Tip 2]

**NDVI Equivalent Status:** [Green/Yellow/Red zone - based on soil moisture and temp data]
"""

def get_historical_land_health(lat: float, lon: float, language: str = "English", days: int = 7) -> dict:
    """Fetch historical soil/climate data and generate a land health report in the specified language."""
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&hourly=soil_temperature_0cm,soil_moisture_0_to_1cm,soil_moisture_1_to_3cm"
            f"&daily=precipitation_sum,et0_fao_evapotranspiration,temperature_2m_max,temperature_2m_min,sunshine_duration"
            f"&past_days={days}"
            f"&forecast_days=1"
            f"&timezone=Asia/Kolkata"
        )
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        daily = data.get("daily", {})
        hourly = data.get("hourly", {})

        # Build daily summary
        days_data = []
        dates = daily.get("time", [])
        for i, date in enumerate(dates):
            day_entry = {
                "date": date,
                "max_temp": daily.get("temperature_2m_max", [None])[i],
                "min_temp": daily.get("temperature_2m_min", [None])[i],
                "rainfall_mm": daily.get("precipitation_sum", [None])[i],
                "evapotranspiration": daily.get("et0_fao_evapotranspiration", [None])[i],
                "sunshine_hours": round((daily.get("sunshine_duration", [0])[i] or 0) / 3600, 1),
            }
            days_data.append(day_entry)

        # Extract soil readings (hourly at 6 AM each day)
        soil_temps = hourly.get("soil_temperature_0cm", [])
        soil_moisture_shallow = hourly.get("soil_moisture_0_to_1cm", [])
        soil_moisture_deep = hourly.get("soil_moisture_1_to_3cm", [])

        # Sample every 24 hours (6 AM reading = index 6, 30, 54...)
        soil_samples = []
        for i in range(0, len(soil_temps), 24):
            if i + 6 < len(soil_temps):
                soil_samples.append({
                    "day": i // 24 + 1,
                    "soil_temp": soil_temps[i + 6],
                    "moisture_shallow": round((soil_moisture_shallow[i + 6] or 0) * 100, 1) if soil_moisture_shallow else None,
                    "moisture_deep": round((soil_moisture_deep[i + 6] or 0) * 100, 1) if soil_moisture_deep else None,
                })

        # Compute summary stats for health score
        avg_moisture = None
        if soil_moisture_shallow:
            valid = [v for v in soil_moisture_shallow if v is not None]
            if valid:
                avg_moisture = round(sum(valid) / len(valid) * 100, 1)

        total_rainfall = sum(r for r in daily.get("precipitation_sum", []) if r is not None)
        avg_temp_max = None
        temps = [t for t in daily.get("temperature_2m_max", []) if t is not None]
        if temps:
            avg_temp_max = round(sum(temps) / len(temps), 1)

        summary_data = {
            "days_analyzed": len(days_data),
            "total_rainfall_mm": round(total_rainfall, 1),
            "avg_max_temperature": avg_temp_max,
            "avg_soil_moisture_pct": avg_moisture,
            "daily_records": days_data[-7:],  # Last 7 days
            "soil_samples": soil_samples[-7:],
        }

        lang_map = {
            "Marathi": "Marathi (मराठी)",
            "Hindi": "Hindi (हिंदी)",
            "English": "English"
        }
        mapped_lang = lang_map.get(language, "English")

        # Get AI health report
        ai_report = get_gemini_response(
            LAND_HEALTH_PROMPT.format(lat=lat, lon=lon, data=str(summary_data), language=mapped_lang)
        )

        return {
            "location": {"lat": lat, "lon": lon},
            "summary": summary_data,
            "ai_report": ai_report,
        }

    except requests.exceptions.Timeout:
        return {"error": "Land health service timed out. Please try again."}
    except Exception as e:
        return {"error": f"Land health fetch error: {str(e)}"}
