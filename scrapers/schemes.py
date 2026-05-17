import os
import json
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from typing import List, Dict
import uuid
from utils.chroma import schemes_collection
from utils.embeddings import embed_text

SCHEMA_URLS = {
    "mahadbt": "https://mahadbt.maharashtra.gov.in/schemes",
    "pmkisan": "https://pmkisan.gov.in/schemes",
}

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "schemes"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def fetch_page(url: str) -> str:
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return ""

def parse_mahadbt(html: str) -> List[Dict]:
    if not html: return []
    soup = BeautifulSoup(html, "lxml")
    cards = []
    # Note: These selectors are examples and might need adjustment for the real site
    for scheme_div in soup.select("div.scheme-card"):
        name = scheme_div.select_one("h3").get_text(strip=True)
        benefit = scheme_div.select_one(".benefit").get_text(strip=True)
        eligibility = scheme_div.select_one(".eligibility").get_text(strip=True)
        apply = scheme_div.select_one(".apply").get_text(strip=True)
        docs = [li.get_text(strip=True) for li in scheme_div.select("ul.documents li")]
        cards.append({
            "scheme_name": name,
            "benefit": benefit,
            "eligibility": eligibility,
            "how_to_apply": apply,
            "documents_needed": docs,
            "state": "Maharashtra",
            "source": "mahadbt",
            "last_updated": "2024-12",
        })
    return cards

def parse_pmkisan(html: str) -> List[Dict]:
    if not html: return []
    soup = BeautifulSoup(html, "lxml")
    cards = []
    for row in soup.select("table.schemes tbody tr"):
        cols = row.find_all("td")
        if len(cols) < 5:
            continue
        cards.append({
            "scheme_name": cols[0].get_text(strip=True),
            "benefit": cols[1].get_text(strip=True),
            "eligibility": cols[2].get_text(strip=True),
            "how_to_apply": cols[3].get_text(strip=True),
            "documents_needed": cols[4].get_text(strip=True).split(","),
            "state": "All India",
            "source": "pmkisan",
            "last_updated": "2024-12",
        })
    return cards

def scrape_and_save():
    all_cards = []
    # Mahadbt
    html_mahadbt = fetch_page(SCHEMA_URLS["mahadbt"])
    all_cards.extend(parse_mahadbt(html_mahadbt))
    # PM Kisan
    html_pmkisan = fetch_page(SCHEMA_URLS["pmkisan"])
    all_cards.extend(parse_pmkisan(html_pmkisan))
    
    # Fallback/Sample data if scraping failed or returned nothing
    if not all_cards:
        all_cards = [
            {
                "scheme_name": "PM Kisan Samman Nidhi",
                "benefit": "₹6000 per year in 3 installments",
                "eligibility": "All land-holding farmers with cultivable land",
                "how_to_apply": "pmkisan.gov.in or nearest CSC center",
                "documents_needed": ["Aadhaar", "Bank passbook", "Land records"],
                "state": "All India",
                "source": "pmkisan",
                "last_updated": "2024-12"
            },
            {
                "scheme_name": "Majhi Ladki Bahin Yojana",
                "benefit": "₹1500 per month (₹18,000 per year)",
                "eligibility": "Women residents of Maharashtra aged 21 to 65 years. Family income must be less than ₹2.5 lakh per year.",
                "how_to_apply": "Apply online through Narishakti Doot App or nearest Anganwadi center/Setu Suvidha Kendra.",
                "documents_needed": ["Aadhaar Card", "Ration Card", "Income Certificate", "Domicile Certificate", "Bank Passbook"],
                "state": "Maharashtra",
                "source": "Maharashtra State Government",
                "last_updated": "2024-12"
            },
            {
                "scheme_name": "Nanaji Deshmukh Krishi Sanjivani Yojana (PoCRA)",
                "benefit": "Financial assistance for sustainable farming, micro-irrigation, and orchard plantation.",
                "eligibility": "Small and marginal farmers in drought-prone areas of Maharashtra.",
                "how_to_apply": "Apply through the official PoCRA portal or via the Gram Panchayat.",
                "documents_needed": ["7/12 Utara", "8A certificate", "Bank details"],
                "state": "Maharashtra",
                "source": "Maharashtra Agriculture Department",
                "last_updated": "2024-12"
            }
        ]

    # Save JSON lines file
    out_path = OUTPUT_DIR / "scheme_cards.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for card in all_cards:
            json.dump(card, f)
            f.write("\n")
    
    # Ingest into ChromaDB
    print(f"Ingesting {len(all_cards)} scheme cards into ChromaDB...")
    texts = [json.dumps(card) for card in all_cards]
    ids = [str(uuid.uuid4()) for _ in all_cards]
    metadatas = all_cards
    embeddings = embed_text(texts)
    
    schemes_collection.add(
        ids=ids,
        documents=texts,
        metadatas=metadatas,
        embeddings=embeddings.tolist()
    )
    print(f"Successfully indexed {len(all_cards)} schemes.")

if __name__ == "__main__":
    scrape_and_save()
