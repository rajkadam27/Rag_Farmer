"""
PDF Summarizer - Extract text from PDF and summarize for farmers
Uses PyPDF2 for extraction and Gemini for AI summarization.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from utils.llm import get_gemini_response

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

PDF_SUMMARY_PROMPT = """You are a helpful government scheme advisor for Maharashtra farmers.

RESPOND ENTIRELY IN THIS LANGUAGE: {language}

A farmer has uploaded a government document/scheme PDF. Extract and summarize the key information.

Document Text (first 3000 chars):
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

def summarize_pdf(file_path: str, language: str = "English") -> str:
    """Extract text from PDF and summarize it for farmers in the specified language."""
    try:
        import pypdf
        text = ""
        with open(file_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages[:10]:  # Max 10 pages
                text += page.extract_text() or ""
                if len(text) > 4000:
                    break

        if not text.strip():
            return "Could not extract readable text from this PDF. It might be scanned images."

        lang_map = {
            "Marathi": "Marathi (मराठी)",
            "Hindi": "Hindi (हिंदी)",
            "English": "English"
        }
        mapped_lang = lang_map.get(language, "English")

        # Limit text to 3000 chars to avoid overwhelming the prompt
        truncated_text = text[:3000]
        prompt = PDF_SUMMARY_PROMPT.format(text=truncated_text, language=mapped_lang)
        
        return get_gemini_response(prompt)

    except ImportError:
        return "PDF processing library not installed. Run: pip install pypdf"
    except Exception as e:
        return f"PDF processing error: {str(e)}"
