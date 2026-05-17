import gradio as gr
import httpx
import os
from dotenv import load_dotenv

load_dotenv()
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api")

def farmer_advisor(query, language):
    if not query:
        return "Please enter a question.", ""
    
    payload = {
        "user_input": query,
        "language": "mar_Deva" if language == "Marathi" else "hin_Deva" if language == "Hindi" else "eng_Latn"
    }
    
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(f"{API_URL}/query", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                answer = data.get("answer", "No answer received.")
                sources = "\n".join([f"- {s}" for s in data.get("sources", [])])
                return answer, sources
            else:
                return f"Error: Backend returned {resp.status_code}", ""
    except Exception as e:
        return f"Error connecting to backend: {e}", ""

# Define the UI
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🚜 Maharashtra Farmer Advisory System")
    gr.Markdown("Ask questions about crops, pests, and government schemes in Marathi, Hindi, or English.")
    
    with gr.Row():
        lang_radio = gr.Radio(["English", "Marathi", "Hindi"], label="Language / भाषा", value="English")
    
    with gr.Row():
        input_text = gr.Textbox(label="Type your question here / आपला प्रश्न येथे टाइप करा", placeholder="e.g. कापूस पिकावर पडणाऱ्या लाल्या रोगावर उपाय काय?")
    
    submit_btn = gr.Button("Get Advice / सल्ला मिळवा", variant="primary")
    
    with gr.Column():
        output_answer = gr.Markdown(label="🤖 Advisory Response")
        output_sources = gr.Markdown(label="📚 Sources")

    submit_btn.click(fn=farmer_advisor, inputs=[input_text, lang_radio], outputs=[output_answer, output_sources])

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=8501)
