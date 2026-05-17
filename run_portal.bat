@echo off
echo Starting Maharashtra Farmer Advisory Portal...
echo Access at http://127.0.0.1:8000
.\venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
pause
