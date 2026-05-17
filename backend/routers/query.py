from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from utils.lang import detect_language, translate
from utils.embeddings import embed_text
from utils.chroma import agronomy_collection, schemes_collection, query_collection
from utils.llm import get_gemini_response

router = APIRouter()

# In-memory conversation store: {user_id: [(question, answer), ...]}
conversation_history: Dict[str, List[Dict]] = {}
MAX_HISTORY = 5  # Keep last 5 exchanges

class QueryPayload(BaseModel):
    user_input: str
    user_id: str | None = None
    language: str | None = None

SYSTEM_PROMPT = """You are the Senior Official Agricultural and Welfare Advisor for the Government of Maharashtra.
Your goal is to provide a highly PROFESSIONAL, STRUCTURED, and POINT-WISE advisory report.

For every query, you MUST structure your response exactly like this:

### 1. Benefits of the [Scheme/Topic]
[Detail the financial, social, or technical benefits in bullet points]

### 2. Eligibility Criteria
[List exactly who qualifies or the conditions required]

### 3. Documents Needed
[List all required certificates, IDs, and records]

### 4. Step-by-Step Action Plan
[Provide a clear, numbered plan of action (Online and Offline methods)]

### 5. Important Contact Points
[List specific offices like Setu Kendra, Anganwadi, or KVK for help]

### Expert Advice for Farmers:
[Provide a concluding expert tip specifically for the rural/farming context]

IMPORTANT:
- Use clear, authoritative, and helpful language.
- If the user refers to a previous question (e.g., "that scheme", "the above"), use the conversation history provided.
- If specific details are missing from the context, provide the best general government procedure.
- Ensure the tone is official yet accessible.
"""

@router.post("/query")
async def handle_query(payload: QueryPayload):
    if not payload.user_input:
        raise HTTPException(status_code=400, detail="Empty query")

    user_id = payload.user_id or "anonymous"

    # 1. Detect language
    user_lang = payload.language or detect_language(payload.user_input)

    # 2. Translate to English if needed
    if user_lang != "eng_Latn":
        english_query = translate(payload.user_input, src_lang=user_lang, tgt_lang="eng_Latn")
    else:
        english_query = payload.user_input

    # 3. Embed query
    query_embedding = embed_text(english_query).tolist()

    # 4. Retrieve from both collections
    agri_results = query_collection(agronomy_collection, query_embedding, n_results=3)
    scheme_results = query_collection(schemes_collection, query_embedding, n_results=2)

    # 5. Combine context
    context_chunks = []
    sources = []

    if agri_results['documents']:
        for i, doc in enumerate(agri_results['documents'][0]):
            context_chunks.append(f"Agronomy Context: {doc}")
            src = agri_results['metadatas'][0][i].get('source', 'Agronomy Knowledge Base')
            if src not in sources:
                sources.append(src)

    if scheme_results['documents']:
        for i, doc in enumerate(scheme_results['documents'][0]):
            context_chunks.append(f"Govt Scheme: {doc}")
            src = scheme_results['metadatas'][0][i].get('scheme_name', 'Government Welfare Scheme')
            if src not in sources:
                sources.append(src)

    full_context = "\n\n".join(context_chunks)

    # 6. Build conversation history context
    history = conversation_history.get(user_id, [])
    history_text = ""
    if history:
        history_text = "\n\nPrevious Conversation:\n"
        for h in history[-MAX_HISTORY:]:
            history_text += f"User: {h['q']}\nAdvisor: {h['a'][:300]}...\n\n"

    # 7. Call LLM with history
    lang_map = {
        "Marathi": "Marathi (मराठी)",
        "Hindi": "Hindi (हिंदी)",
        "English": "English"
    }
    mapped_lang = lang_map.get(user_lang, "English")

    prompt = f"RESPOND ENTIRELY IN THE {mapped_lang} LANGUAGE.\n\nContext:\n{full_context}{history_text}\n\nCurrent Question: {english_query}"
    try:
        english_answer = get_gemini_response(prompt, system_instruction=SYSTEM_PROMPT)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM Error: {str(e)}")

    # 8. Store in conversation history
    if user_id not in conversation_history:
        conversation_history[user_id] = []
    conversation_history[user_id].append({"q": english_query, "a": english_answer})
    # Trim to max history
    if len(conversation_history[user_id]) > MAX_HISTORY:
        conversation_history[user_id] = conversation_history[user_id][-MAX_HISTORY:]

    # 9. No need to translate answer back as we instructed LLM directly
    final_answer = english_answer

    return {
        "original_query": payload.user_input,
        "detected_language": user_lang,
        "english_query": english_query,
        "answer": final_answer,
        "english_answer": english_answer,
        "sources": sources,
        "conversation_turns": len(conversation_history.get(user_id, []))
    }

@router.delete("/query/history/{user_id}")
async def clear_history(user_id: str):
    """Clear conversation history for a user."""
    if user_id in conversation_history:
        del conversation_history[user_id]
    return {"status": "history cleared", "user_id": user_id}
