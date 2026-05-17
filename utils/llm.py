import os
import google.generativeai as genai
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

def get_gemini_response(prompt: str, system_instruction: str = "") -> str:
    """Get a response from either Gemini (preferred) or OpenAI, with robust key loading."""
    
    # 1. Try standard dotenv loading
    root_dir = Path(__file__).resolve().parent.parent
    env_path = root_dir / ".env"
    load_dotenv(dotenv_path=env_path, override=True)
    
    gemini_key = os.getenv("GEMINI_API_KEY")

    # 2. Manual fallback if dotenv fails (sometimes happens on Windows)
    if not gemini_key and env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("GEMINI_API_KEY="):
                        gemini_key = line.split("=", 1)[1].strip()
                        os.environ["GEMINI_API_KEY"] = gemini_key
                        break
        except Exception as e:
            print(f"Manual .env read error: {e}")

    openai_key = os.getenv("OPENAI_API_KEY")

    # Try Gemini first
    if gemini_key:
        try:
            genai.configure(api_key=gemini_key)

            # Using Gemini 2.5 Flash for high speed and instruction following
            model_kwargs = {"model_name": "models/gemini-2.5-flash"}
            if system_instruction and system_instruction.strip():
                model_kwargs["system_instruction"] = system_instruction

            model = genai.GenerativeModel(**model_kwargs)

            # Ensure prompt is never empty
            safe_prompt = prompt.strip() if prompt else "Hello"
            response = model.generate_content(safe_prompt)
            return response.text
        except Exception as e:
            # Return the actual error to the UI for debugging
            return f"Gemini API Error: {str(e)} (Model: gemini-2.5-flash)"

    # Fallback to OpenAI
    if openai_key:
        try:
            client = OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"OpenAI API Error: {str(e)}"
            
    return f"Error: No working API key found. Checked at {env_path}. Found key: {'Yes' if gemini_key else 'No'}"
