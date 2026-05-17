from fastapi import APIRouter, File, UploadFile, HTTPException
from typing import Dict
import os
import tempfile
from pathlib import Path
import subprocess

router = APIRouter()

# Path to Whisper model (assumed downloaded in project root "models/large-v3.bin")
WHISPER_MODEL_PATH = Path(__file__).parent.parent.parent / "models" / "large-v3.bin"
MODEL_AVAILABLE = WHISPER_MODEL_PATH.exists()

@router.post("/voice")
async def transcribe_voice(file: UploadFile = File(...)):
    if not MODEL_AVAILABLE:
        raise HTTPException(status_code=503, detail="Whisper voice model not found on server. Please upload models/large-v3.bin")
    """Accept an audio file (wav, mp3) and return the transcribed text using whispercpp.
    This is a minimal wrapper; for production you would stream the file to whispercpp.
    """
    # Save uploaded file to a temporary location
    suffix = Path(file.filename).suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = Path(tmp.name)
        content = await file.read()
        tmp.write(content)
    # Call whispercpp binary (assumes whispercpp executable is in PATH or project root)
    # Using the "whisper" CLI from whispercpp repo
    cmd = ["whisper", str(tmp_path), "-model", str(WHISPER_MODEL_PATH), "-language", "en", "-output", "txt"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except Exception as e:
        os.remove(tmp_path)
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")
    os.remove(tmp_path)
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Whisper error: {result.stderr}")
    # Whisper writes a .txt file next to the audio file
    txt_path = tmp_path.with_suffix('.txt')
    if not txt_path.exists():
        raise HTTPException(status_code=500, detail="Transcription output missing")
    transcription = txt_path.read_text(encoding="utf-8").strip()
    txt_path.unlink(missing_ok=True)
    return {"transcription": transcription}
