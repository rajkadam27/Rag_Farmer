"""
Land Health Utility - Historical soil & climate data from Open-Meteo
Provides multi-day soil health trend data for NDVI-like field assessment.
No API key required.
"""
import hashlib
import random

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

NDVI_ZONING_PROMPT_APPEND = """

Simulated Multispectral NDVI Analytics:
{ndvi_data}

Also include this section:

**AI PRECISION ZONING REPORT:**
- Average NDVI: [score and health class]
- Strong Crop Vigor Zone: [best zone and what it means]
- Stress Patch: [lowest NDVI zone and likely cause]
- Border/Drip-Line Action: [one precise inspection or irrigation action]
- Next 48 Hours: [one practical task for the farmer]
"""


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _status_from_ndvi(score: float) -> str:
    if score >= 0.62:
        return "Healthy"
    if score >= 0.45:
        return "Moderate"
    if score >= 0.32:
        return "Water Stressed"
    return "Critical"


def _zone_color(score: float) -> str:
    if score >= 0.70:
        return "#0b5d1e"
    if score >= 0.58:
        return "#2f9e44"
    if score >= 0.45:
        return "#f2c94c"
    if score >= 0.32:
        return "#f97316"
    return "#dc2626"


def generate_ndvi_simulation(lat: float, lon: float, summary_data: dict) -> dict:
    """Create deterministic simulated NDVI zones and spectral values for the selected field."""
    seed = int(hashlib.sha256(f"{lat:.5f}:{lon:.5f}".encode("utf-8")).hexdigest()[:12], 16)
    rng = random.Random(seed)

    moisture = summary_data.get("avg_soil_moisture_pct")
    moisture = 14.0 if moisture is None else float(moisture)

    rainfall = float(summary_data.get("total_rainfall_mm") or 0)
    avg_temp = summary_data.get("avg_max_temperature")
    avg_temp = 32.0 if avg_temp is None else float(avg_temp)

    latest_evapo = 3.2
    daily_records = summary_data.get("daily_records") or []
    if daily_records:
        latest_evapo = float(daily_records[-1].get("evapotranspiration") or latest_evapo)

    moisture_component = _clamp(moisture / 32.0, 0.0, 1.0)
    rainfall_component = _clamp(rainfall / 45.0, 0.0, 1.0)
    heat_penalty = _clamp((avg_temp - 34.0) * 0.018, 0.0, 0.16)
    evaporation_penalty = _clamp((latest_evapo - 4.0) * 0.025, 0.0, 0.10)
    base_score = 0.25 + (0.43 * moisture_component) + (0.14 * rainfall_component)
    base_score = _clamp(base_score - heat_penalty - evaporation_penalty + rng.uniform(-0.035, 0.035), 0.16, 0.86)

    zone_templates = [
        ("North ridge", 120, 0, 150, 120, 0.07),
        ("North-east corner", 100, 120, 130, 120, 0.03),
        ("Central canopy", 0, 0, 170, 145, 0.10),
        ("West strip", -10, -135, 115, 170, -0.03),
        ("East drip line", -5, 140, 115, 170, -0.01),
        ("South-west patch", -125, -90, 145, 125, -0.14),
        ("South border", -135, 80, 165, 120, -0.18),
    ]

    zones = []
    for name, north_m, east_m, width_m, height_m, bias in zone_templates:
        zone_score = _clamp(base_score + bias + rng.uniform(-0.07, 0.07), 0.10, 0.91)
        if "South border" in name:
            zone_score = _clamp(min(zone_score, base_score - rng.uniform(0.09, 0.22)), 0.10, 0.91)
        zones.append({
            "name": name,
            "ndvi": round(zone_score, 2),
            "status": _status_from_ndvi(zone_score),
            "color": _zone_color(zone_score),
            "offset_north_m": north_m,
            "offset_east_m": east_m,
            "width_m": width_m,
            "height_m": height_m,
        })

    avg_ndvi = round(sum(zone["ndvi"] for zone in zones) / len(zones), 2)
    min_zone = min(zones, key=lambda item: item["ndvi"])
    max_zone = max(zones, key=lambda item: item["ndvi"])
    red_reflectance = round(_clamp(0.32 - (avg_ndvi * 0.19) + rng.uniform(-0.015, 0.015), 0.08, 0.34), 3)
    nir_reflectance = round(_clamp(0.28 + (avg_ndvi * 0.56) + rng.uniform(-0.015, 0.015), 0.25, 0.82), 3)

    curve = []
    for wavelength in [560, 620, 665, 705, 740, 783, 842, 865]:
        red_peak = 1 - min(abs(wavelength - 665) / 210, 1)
        nir_peak = max(0, min((wavelength - 700) / 150, 1))
        curve.append({
            "wavelength_nm": wavelength,
            "red": round(_clamp(red_reflectance + red_peak * 0.055 - nir_peak * 0.025, 0.04, 0.42), 3),
            "nir": round(_clamp(nir_reflectance - (1 - nir_peak) * 0.20 + red_peak * 0.018, 0.12, 0.86), 3),
        })

    return {
        "score": avg_ndvi,
        "status": _status_from_ndvi(avg_ndvi),
        "min_zone": min_zone,
        "max_zone": max_zone,
        "nir_reflectance": nir_reflectance,
        "red_reflectance": red_reflectance,
        "zones": zones,
        "reflectance_curve": curve,
        "legend": [
            {"label": "Dense healthy crop", "color": "#0b5d1e", "range": "0.70+"},
            {"label": "Active vegetation", "color": "#2f9e44", "range": "0.58-0.69"},
            {"label": "Early stress", "color": "#f2c94c", "range": "0.45-0.57"},
            {"label": "Water/nitrogen stress", "color": "#f97316", "range": "0.32-0.44"},
            {"label": "Bare soil/disease patch", "color": "#dc2626", "range": "<0.32"},
        ],
    }


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
        ndvi_simulation = generate_ndvi_simulation(lat, lon, summary_data)

        lang_map = {
            "Marathi": "Marathi (मराठी)",
            "Hindi": "Hindi (हिंदी)",
            "English": "English"
        }
        mapped_lang = lang_map.get(language, "English")

        # Get AI health report
        ai_report = get_gemini_response(
            (LAND_HEALTH_PROMPT + NDVI_ZONING_PROMPT_APPEND).format(
                lat=lat,
                lon=lon,
                data=str(summary_data),
                ndvi_data=str(ndvi_simulation),
                language=mapped_lang,
            )
        )

        return {
            "location": {"lat": lat, "lon": lon},
            "summary": summary_data,
            "ndvi_simulation": ndvi_simulation,
            "ai_report": ai_report,
        }

    except requests.exceptions.Timeout:
        return {"error": "Land health service timed out. Please try again."}
    except Exception as e:
        return {"error": f"Land health fetch error: {str(e)}"}
