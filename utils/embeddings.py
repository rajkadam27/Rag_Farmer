import os
import numpy as np
import google.generativeai as genai
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

def embed_text(texts):
    """Use API for embeddings to save local RAM. Local model is disabled to prevent MemoryErrors."""
    if isinstance(texts, str):
        texts = [texts]
    
    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    # Try Gemini Embeddings
    if gemini_key:
        try:
            genai.configure(api_key=gemini_key)
            result = genai.embed_content(
                model="models/gemini-embedding-001",
                content=texts,
                task_type="retrieval_document"
            )
            return np.array(result['embedding'])
        except Exception as e:
            print(f"Gemini Embedding Error: {e}")

    # Try OpenAI Embeddings
    if openai_key:
        try:
            client = OpenAI(api_key=openai_key)
            response = client.embeddings.create(
                input=texts,
                model="text-embedding-3-small"
            )
            return np.array([data.embedding for data in response.data])
        except Exception as e:
            print(f"OpenAI Embedding Error: {e}")
            
    raise Exception("No working API key for embeddings (Gemini/OpenAI). Local model is disabled due to memory limits.")
