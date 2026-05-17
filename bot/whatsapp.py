from fastapi import APIRouter, Request, Form, Response
import httpx
import os
from twilio.twiml.messaging_response import MessagingResponse

router = APIRouter()

API_URL = os.getenv("API_URL", "http://localhost:8000/api")

@router.post("/whatsapp")
async def whatsapp_bot(From: str = Form(...), Body: str = Form(...)):
    """Webhook for Twilio WhatsApp integration."""
    response = MessagingResponse()
    
    # Call our query API
    payload = {"user_input": Body, "user_id": From}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{API_URL}/query", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                answer = data.get("answer", "I couldn't process your request.")
                
                # Sanitize for WhatsApp (WhatsApp uses * for bold, doesn't like ###)
                answer = answer.replace("### ", "*").replace("## ", "*")
                
                # Limit length for Sandbox stability (Twilio Sandbox can be picky with long msgs)
                if len(answer) > 1500:
                    answer = answer[:1490] + "...\n\n(Read full report on our website)"
                
                response.message(answer)
            else:
                response.message("Sorry, I'm having trouble connecting to my knowledge base.")
    except Exception as e:
        print(f"DEBUG: WhatsApp Bot Error: {e}", flush=True)
        response.message("An error occurred while processing your request.")

    twiml = str(response)
    return Response(content=twiml, media_type="text/xml")
