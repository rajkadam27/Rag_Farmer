import os
from langdetect import detect
import google.generativeai as genai
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

def detect_language(text: str) -> str:
    """Detect language locally using langdetect and return human-readable name."""
    try:
        iso = detect(text)
        mapping = {
            "mr": "Marathi",
            "hi": "Hindi",
            "en": "English",
        }
        return mapping.get(iso, "English")
    except:
        return "English"

def translate(text: str, src_lang: str, tgt_lang: str) -> str:
    """Translate using Gemini or OpenAI with hot-reloading keys."""
    if src_lang == tgt_lang:
        return text
    
    # Reload keys
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(dotenv_path=env_path, override=True)
    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    prompt = f"Translate the following text from {src_lang} to {tgt_lang}. Return ONLY the translated text: '{text}'"
    
    # Try Gemini
    if gemini_key:
        try:
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel("gemini-flash-latest")
            response = model.generate_content(prompt)
            return response.text.strip()
        except:
            pass

    # Try OpenAI
    if openai_key:
        try:
            client = OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content.strip()
        except:
            pass
            
    return text
