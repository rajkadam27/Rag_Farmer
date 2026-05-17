"""
AI Vision - Crop Pest & Disease Diagnosis
Uses Gemini Vision (multimodal) via the established llm pattern.
"""
import os
import base64
import google.generativeai as genai
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image

# Always load from project root .env using absolute path
root_dir = Path(__file__).resolve().parent.parent
env_path = root_dir / ".env"
load_dotenv(dotenv_path=env_path, override=True)

VISION_PROMPT = """You are an expert Agricultural Scientist and Plant Pathologist for Indian farms.

RESPOND ENTIRELY IN THIS LANGUAGE: {language}

Analyze this image carefully and provide a structured diagnosis.

Respond EXACTLY in this format:

**Crop Identified:** [Name of crop or plant]

**Diagnosis:**
[What disease, pest, or deficiency is visible. Be specific. If the plant is healthy, say so.]

**Severity:** [Mild / Moderate / Severe / Healthy]

**Recommended Treatment:**
1. [First treatment step - prefer organic options first]
2. [Second step - chemical if needed, with Indian brand names]
3. [Preventive measure for future]

**Estimated Yield Impact:** [e.g., "10-20% loss if untreated within 1 week"]

**Expert Tip:** [One practical tip specific to Maharashtra farmers]

If this is not a plant image, clearly state: "Please upload a photo of your crop or plant."
"""

def diagnose_crop_image(image_path: str, language: str = "English") -> str:
    """Diagnose a crop image using Gemini Vision."""
    # 1. Try standard dotenv loading
    root_dir = Path(__file__).resolve().parent.parent
    env_path = root_dir / ".env"
    load_dotenv(dotenv_path=env_path, override=True)
    
    gemini_key = os.getenv("GEMINI_API_KEY")

    # 2. Manual fallback if dotenv fails
    if not gemini_key and env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("GEMINI_API_KEY="):
                        gemini_key = line.split("=", 1)[1].strip()
                        os.environ["GEMINI_API_KEY"] = gemini_key
                        break
        except Exception as e:
            print(f"Manual .env read error in vision.py: {e}")

    if not gemini_key:
        return f"Error: GEMINI_API_KEY not found in {env_path}"

    try:
        genai.configure(api_key=gemini_key)
        # Using Gemini 2.5 Flash for multimodal diagnosis (highly accurate)
        model = genai.GenerativeModel("gemini-2.5-flash")

        lang_map = {
            "Marathi": "Marathi (मराठी)",
            "Hindi": "Hindi (हिंदी)",
            "English": "English"
        }
        mapped_lang = lang_map.get(language, "English")

        img = Image.open(image_path)
        response = model.generate_content([VISION_PROMPT.format(language=mapped_lang), img])
        return response.text

    except Exception as e:
        print(f"Vision Error in vision.py (tried gemini-2.5-flash): {e}")
        # Fallback: try reading as base64
        try:
            with open(image_path, "rb") as f:
                img_data = base64.b64encode(f.read()).decode()
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content([
                VISION_PROMPT.format(language=mapped_lang),
                {"mime_type": "image/jpeg", "data": img_data}
            ])
            return response.text
        except Exception as e2:
            return f"Diagnosis Error: {str(e2)}"
