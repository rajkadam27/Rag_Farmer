import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

# Import routers
from backend.routers import query, voice

app = FastAPI(title="Maharashtra Farmer Advisory System")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(query.router, prefix="/api")
app.include_router(voice.router, prefix="/api")

# WhatsApp Bot Integration
from bot.whatsapp import router as whatsapp_router
app.include_router(whatsapp_router, prefix="/api")

# New AI Features Router
from backend.routers import features
app.include_router(features.router, prefix="/api")

# Setup Templates & Static Files
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_advisor(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="advisor.html", 
        context={"active_page": "advisor"}
    )

@app.get("/schemes", response_class=HTMLResponse)
async def read_schemes(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="schemes.html", 
        context={"active_page": "schemes", "page_title": "Government Welfare Schemes"}
    )

@app.get("/agronomy", response_class=HTMLResponse)
async def read_agronomy(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="agronomy.html", 
        context={"active_page": "agronomy", "page_title": "Crop Protection & Agronomy"}
    )

@app.get("/history", response_class=HTMLResponse)
async def read_history(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="history.html", 
        context={"active_page": "history", "page_title": "Consultation History"}
    )

@app.get("/settings", response_class=HTMLResponse)
async def read_settings(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="settings.html", 
        context={"active_page": "settings", "page_title": "System Settings"}
    )

@app.get("/calculators", response_class=HTMLResponse)
async def read_calculators(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="calculators.html",
        context={"active_page": "calculators", "page_title": "Agricultural Calculators"}
    )

@app.get("/calendar", response_class=HTMLResponse)
async def read_calendar(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="calendar.html",
        context={"active_page": "calendar", "page_title": "Sowing Calendar"}
    )

@app.get("/directory", response_class=HTMLResponse)
async def read_directory(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="directory.html",
        context={"active_page": "directory", "page_title": "Expert Directory"}
    )

@app.get("/diagnosis", response_class=HTMLResponse)
async def read_diagnosis(request: Request):
    return templates.TemplateResponse(request=request, name="diagnosis.html",
        context={"active_page": "diagnosis", "page_title": "AI Crop Diagnosis"})

@app.get("/voice", response_class=HTMLResponse)
async def read_voice(request: Request):
    return templates.TemplateResponse(request=request, name="voice.html",
        context={"active_page": "voice", "page_title": "Voice Assistant"})

@app.get("/mandi", response_class=HTMLResponse)
async def read_mandi(request: Request):
    return templates.TemplateResponse(request=request, name="mandi.html",
        context={"active_page": "mandi", "page_title": "Mandi Prices"})

@app.get("/weather-advice", response_class=HTMLResponse)
async def read_weather(request: Request):
    return templates.TemplateResponse(request=request, name="weather_advice.html",
        context={"active_page": "weather", "page_title": "Weather Farm Advice"})

@app.get("/pdf-tool", response_class=HTMLResponse)
async def read_pdf_tool(request: Request):
    return templates.TemplateResponse(request=request, name="pdf_tool.html",
        context={"active_page": "pdf", "page_title": "PDF Summarizer"})

@app.get("/field-health", response_class=HTMLResponse)
async def read_field_health(request: Request):
    return templates.TemplateResponse(request=request, name="field_health.html",
        context={"active_page": "field", "page_title": "Field Health Monitor"})

@app.get("/scheme-checker", response_class=HTMLResponse)
async def read_scheme_checker(request: Request):
    return templates.TemplateResponse(request=request, name="scheme_checker.html",
        context={"active_page": "scheme", "page_title": "Scheme Eligibility Checker"})

@app.get("/land-health-map", response_class=HTMLResponse)
async def read_land_health_map(request: Request):
    return templates.TemplateResponse(request=request, name="land_health.html",
        context={"active_page": "landhealth", "page_title": "Land Health Dashboard"})

@app.get("/health")
async def health_check():
    return {"status": "ok"}
