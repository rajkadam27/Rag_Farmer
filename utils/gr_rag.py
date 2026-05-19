"""
GR RAG Utility - Query Government Resolutions using vector search + Gemini.
"""
from utils.embeddings import embed_text
from utils.chroma import gr_collection, query_collection
from utils.llm import get_gemini_response

LANG_MAP = {
    "Marathi": "Marathi (मराठी)",
    "Hindi": "Hindi (हिंदी)",
    "English": "English",
}

GR_SYSTEM_PROMPT = """You are the Official Government Resolution (GR) Expert for Maharashtra.
You MUST answer farmer queries using ONLY the GR context provided below.

CRITICAL RULES:
1. Always cite the exact GR Number and Date in your response.
2. Clearly state eligibility criteria, subsidy amounts, and how to apply.
3. If the context does not contain relevant information, say so clearly.
4. Format your response with clear sections: GR Reference, Benefits, Eligibility, How to Apply.
5. Be precise with monetary amounts — use exact figures from the GR.
"""


def query_gr(question: str, lang: str = "English") -> dict:
    """
    Embed the question, retrieve relevant GRs, and generate a cited answer.
    Returns: {"answer": str, "sources": list of GR references}
    """
    mapped_lang = LANG_MAP.get(lang, "English")

    # Embed the question
    query_embedding = embed_text(question).tolist()

    # Retrieve top-3 relevant GR chunks
    results = query_collection(gr_collection, query_embedding, n_results=3)

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    if not documents:
        return {
            "answer": "No relevant Government Resolutions found in the database.",
            "sources": []
        }

    # Build context from retrieved GRs
    context_parts = []
    sources = []
    for i, (doc, meta) in enumerate(zip(documents, metadatas)):
        gr_ref = f"{meta.get('gr_number', 'N/A')} ({meta.get('date', 'N/A')})"
        context_parts.append(f"--- GR #{i+1}: {gr_ref} ---\n{doc}")
        sources.append({
            "gr_number": meta.get("gr_number", "N/A"),
            "date": meta.get("date", "N/A"),
            "subject": meta.get("subject", "N/A"),
            "department": meta.get("department", "N/A"),
        })

    context = "\n\n".join(context_parts)

    prompt = f"""RESPOND ENTIRELY IN {mapped_lang}.

The farmer is asking: "{question}"

Here are the relevant Government Resolutions (GRs) from the Maharashtra state database:

{context}

Based on these official GRs, provide a clear, structured answer with:
## 📋 Relevant GR Reference
[Cite GR number and date]

## 💰 Benefits & Subsidy Details
[Exact amounts and percentages]

## ✅ Eligibility Criteria
[Who qualifies]

## 📝 How to Apply
[Step-by-step application process]

## ⚠️ Important Notes
[Deadlines, districts, documents needed]

If no GR directly answers the query, mention the closest relevant GR and suggest the farmer contact the nearest Krishi Seva Kendra or Setu Suvidha Kendra.
"""

    answer = get_gemini_response(prompt, system_instruction=GR_SYSTEM_PROMPT)

    return {
        "answer": answer,
        "sources": sources
    }
