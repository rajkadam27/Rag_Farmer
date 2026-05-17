"""
PDF Summarizer - Extract text from PDF and summarize for farmers.
Uses Gemini's native PDF/Vision capabilities for advanced OCR, and falls back to pypdf.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from utils.llm import get_gemini_response

# Standard Prompt for Text-based fallback
PDF_SUMMARY_PROMPT = """You are a helpful government scheme advisor for Maharashtra farmers.

RESPOND ENTIRELY IN THIS LANGUAGE: {language}

A farmer has uploaded a government document/scheme PDF. Extract and summarize the key information.

Document Text (extracted):
{text}

Provide a clear summary in this EXACT format:

**Scheme/Document Name:** [Extract the official name]

**What is this about?**
[2-3 sentences in simple language that any farmer can understand]

**Who can apply? (Eligibility)**
- [Criterion 1]
- [Criterion 2]
- [Criterion 3]

**What benefits will you get?**
- [Benefit 1 with amount if mentioned]
- [Benefit 2]

**Important Dates:**
- Application Deadline: [Date or "Not mentioned"]
- Scheme Valid Till: [Date or "Ongoing"]

**How to Apply (Steps):**
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Documents Required:**
- [Document 1]
- [Document 2]

**Farmer's Tip:** [One expert tip to maximize benefit from this scheme]

If the document is not about a government scheme, summarize it simply for a farmer's understanding.
"""

# Native PDF Prompt (when uploading the PDF file directly to Gemini)
PDF_SUMMARY_PROMPT_NATIVE = """You are an expert government scheme advisor and agriculture consultant for Maharashtra farmers.

RESPOND ENTIRELY IN THIS LANGUAGE: {language}

You are provided with a complete PDF document uploaded by a farmer. It may be a government scheme brochure, guidelines, or land record (like 7/12 extract). 
Analyze the entire document carefully, perform OCR if it is scanned, and summarize the key information.

Provide a clear, detailed, and highly accurate summary in this EXACT format:

**Scheme/Document Name:** [Extract the official name / Title of the document]

**What is this about?**
[2-3 sentences in simple language that any farmer can easily understand]

**Who can apply? (Eligibility)**
- [Criterion 1, e.g., land size, category, crop type]
- [Criterion 2]
- [Criterion 3]

**What benefits will you get?**
- [Benefit 1 with exact subsidy amount/percentage if mentioned]
- [Benefit 2]

**Important Dates:**
- Application Deadline: [Specific Date or "Not mentioned"]
- Scheme Valid Till: [Date or "Ongoing"]

**How to Apply (Steps):**
1. [Step 1 - Online portal link or offline office location]
2. [Step 2]
3. [Step 3]

**Documents Required:**
- [Document 1, e.g., Aadhaar Card, 7/12 Extract]
- [Document 2]

**Farmer's Tip:** [One expert piece of advice on how the farmer can maximize their benefits, avoid rejection, or combine with other schemes]

If the document is not about a government scheme (e.g., it is a land document, laboratory test, or crop guide), adapt the format to summarize it simply and extract the key actionable takeaways for a farmer's understanding.
"""

def summarize_pdf(file_path: str, language: str = "English") -> str:
    """
    Extract text/pages from PDF and summarize it for farmers.
    Attempts Gemini's native PDF Upload/Vision feature first (flawless for scanned documents).
    Falls back to pypdf text extraction for other keys or free-tier failures.
    """
    # 1. Load keys
    root_dir = Path(__file__).resolve().parent.parent
    env_path = root_dir / ".env"
    load_dotenv(dotenv_path=env_path, override=True)
    
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key and env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("GEMINI_API_KEY="):
                        gemini_key = line.split("=", 1)[1].strip()
                        break
        except Exception:
            pass

    lang_map = {
        "Marathi": "Marathi (मराठी)",
        "Hindi": "Hindi (हिंदी)",
        "English": "English"
    }
    mapped_lang = lang_map.get(language, "English")

    # 2. Try Gemini Native Multimodal PDF Processing first (Highly robust, handles scanned images & OCR)
    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            
            # Upload the PDF to Gemini File API
            uploaded_file = genai.upload_file(path=file_path, mime_type="application/pdf")
            
            # Setup model (Gemini 2.5 Flash has a native 1M+ token context window and reads PDFs)
            model = genai.GenerativeModel("models/gemini-2.5-flash")
            
            # Format prompt for the PDF summary
            prompt = PDF_SUMMARY_PROMPT_NATIVE.format(language=mapped_lang)
            
            response = model.generate_content([uploaded_file, prompt])
            
            # Cleanup File from Google API
            try:
                uploaded_file.delete()
            except Exception:
                pass
                
            if response and response.text:
                return response.text
        except Exception as e:
            # If native upload fails (e.g. Free Tier limitations on File API), fallback to Text Extraction
            print(f"Gemini Native PDF processing failed: {e}. Falling back to text extraction...")

    # 3. Fallback: PyPDF text extraction
    try:
        import pypdf
        text = ""
        with open(file_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            # Increase limit from 10 pages to 50 pages and character limit to 60,000 for comprehensive summaries
            for page in reader.pages[:50]:
                text += page.extract_text() or ""
                if len(text) > 60000:
                    break

        if not text.strip():
            return (
                "Could not extract readable text from this PDF. It appears to be a scanned image-only PDF. "
                "Please make sure your Gemini API Key is working, as scanned PDFs require the Gemini Native "
                "Multimodal feature to perform OCR and read the document!"
            )

        # Truncate text to 40,000 chars to fit standard context limits safely
        truncated_text = text[:40000]
        prompt = PDF_SUMMARY_PROMPT.format(text=truncated_text, language=mapped_lang)
        
        return get_gemini_response(prompt)

    except ImportError:
        return "PDF processing library not installed. Run: pip install pypdf"
    except Exception as e:
        return f"PDF processing error: {str(e)}"


def extract_pdf_text(file_path: str) -> str:
    """
    Extract text from the first 25 pages of a PDF (up to 25,000 characters)
    to serve as high-quality local context for interactive follow-up Q&A.
    """
    try:
        import pypdf
        text = ""
        with open(file_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages[:25]:
                text += page.extract_text() or ""
                if len(text) > 25000:
                    break
        return text.strip()
    except Exception as e:
        print(f"Error extracting PDF text context: {e}")
        return ""


