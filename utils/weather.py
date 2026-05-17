"""
Weather Utility - Hyperlocal weather + AI farming advice
Uses OpenWeatherMap API (free tier).
"""
import os
import requests
from pathlib import Path
from dotenv import load_dotenv
from utils.llm import get_gemini_response

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

WEATHER_ADVICE_PROMPT = """You are an expert agricultural advisor for Maharashtra, India.

RESPOND ENTIRELY IN THIS LANGUAGE: {language}

Based on the weather data below, provide CONCISE and ACTIONABLE farming advice.

Weather Data: {weather_data}

Provide advice in this format:

**Today's Farm Advisory:**
- [2-3 specific actions the farmer should take TODAY based on this weather]

**Irrigation Advice:** [Should they irrigate or not, and why]

**Spray/Pesticide Advice:** [Is it safe to spray today? Wind/rain considerations]

**Crop Alert:** [Any weather-related crop risk in next 24 hours]

Keep it brief, practical, and specific for Indian farmers.
"""

def get_weather_advice(city: str, lang: str = "English") -> dict:
    """Fetch weather and generate farming advice."""
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return {"error": "OPENWEATHER_API_KEY not set in .env"}

    try:
        # Step 1: Geocode city
        geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city},IN&limit=1&appid={api_key}"
        geo_resp = requests.get(geo_url, timeout=10).json()
        if not geo_resp:
            return {"error": f"City '{city}' not found. Try 'Satara', 'Nagpur', 'Pune'"}

        lat, lon = geo_resp[0]["lat"], geo_resp[0]["lon"]

        # Step 2: Fetch weather
        weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
        weather = requests.get(weather_url, timeout=10).json()

        weather_data = {
            "city": city,
            "temperature": round(weather["main"]["temp"], 1),
            "feels_like": round(weather["main"]["feels_like"], 1),
            "humidity": weather["main"]["humidity"],
            "condition": weather["weather"][0]["description"].title(),
            "wind_speed": weather["wind"]["speed"],
            "clouds": weather["clouds"]["all"],
        }

        # Step 3: AI farming advice
        lang_map = {
            "Marathi": "Marathi (मराठी)",
            "Hindi": "Hindi (हिंदी)",
            "English": "English"
        }
        mapped_lang = lang_map.get(lang, "English")

        prompt = WEATHER_ADVICE_PROMPT.format(
            weather_data=str(weather_data),
            language=mapped_lang
        )
        
        advice = get_gemini_response(prompt)
        
        return {
            "weather": weather_data,
            "advice": advice
        }
        
    except requests.exceptions.Timeout:
        return {"error": "Weather service timed out."}
    except Exception as e:
        return {"error": f"Failed to get weather data: {str(e)}"}
