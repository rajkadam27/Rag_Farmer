import streamlit as st
import httpx
import os

API_URL = os.getenv("API_URL", "http://localhost:8000/api")

st.set_page_config(page_title="Maharashtra Farmer Advisor", layout="wide", page_icon="🚜")

st.title("🚜 Maharashtra Farmer Advisory System")
st.markdown("""
Welcome to the Farmer Advisory System. You can ask questions about crops, pests, and government schemes in **Marathi, Hindi, or English**.
""")

# Sidebar for language settings
with st.sidebar:
    st.header("Settings")
    lang_option = st.selectbox("Language / भाषा", ["Auto-detect", "Marathi", "Hindi", "English"])
    lang_map = {"Marathi": "mar_Deva", "Hindi": "hin_Deva", "English": "eng_Latn", "Auto-detect": None}
    selected_lang = lang_map[lang_option]

# Main UI
col1, col2 = st.columns([2, 1])

with col1:
    user_query = st.text_area("Type your question here / आपला प्रश्न येथे टाइप करा", height=100)
    
    # Voice upload
    voice_file = st.file_uploader("Or upload a voice query (wav/mp3) / किंवा आवाज फाइल अपलोड करा", type=["wav", "mp3"])

    if st.button("Submit Query / प्रश्न पाठवा"):
        if not user_query and not voice_file:
            st.warning("Please enter a query or upload a voice file.")
        else:
            with st.spinner("Processing your request..."):
                payload = {"user_input": user_query or "", "language": selected_lang}
                
                # Voice handling
                if voice_file:
                    try:
                        with httpx.Client() as client:
                            voice_resp = client.post(f"{API_URL}/voice", files={"file": (voice_file.name, voice_file.read(), voice_file.type)})
                            if voice_resp.status_code == 200:
                                transcription = voice_resp.json().get("transcription", "")
                                payload["user_input"] = transcription
                                st.info(f"Transcribed: {transcription}")
                            else:
                                st.error("Voice transcription failed.")
                                st.stop()
                    except Exception as e:
                        st.error(f"Error connecting to Voice API: {e}")
                        st.stop()

                # Query handling
                try:
                    with httpx.Client(timeout=30.0) as client:
                        resp = client.post(f"{API_URL}/query", json=payload)
                        if resp.status_code == 200:
                            data = resp.json()
                            st.subheader("🤖 Advisory Response")
                            st.success(data.get("answer", ""))
                            
                            with st.expander("Show Original Translation (English)"):
                                st.write(data.get("english_answer", ""))
                            
                            if data.get("sources"):
                                st.subheader("📚 Sources & References")
                                for src in data["sources"]:
                                    st.info(f"Source: {src}")
                        else:
                            st.error(f"Error: {resp.text}")
                except Exception as e:
                    st.error(f"Connection failed: {e}")

with col2:
    st.subheader("How it works")
    st.write("""
    1. **Language Detection**: Automatically identifies if you speak Marathi or Hindi.
    2. **Retrieval**: Searches across official crop guides and government scheme portals.
    3. **AI Generation**: Uses a large language model to synthesize a personalized answer.
    4. **Translation**: Delivers the answer back in your preferred language.
    """)
    
    st.subheader("Sample Questions")
    st.write("- कापूस पिकावर पडणाऱ्या लाल्या रोगावर उपाय काय?")
    st.write("- PM-Kisan योजनेसाठी पात्रता काय आहे?")
    st.write("- How to control pests in soybean?")
