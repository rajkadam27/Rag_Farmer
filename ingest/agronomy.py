import os
from pathlib import Path
from pdfminer.high_level import extract_text
from utils.chroma import agronomy_collection
from utils.embeddings import embed_text
import uuid

DATA_DIR = Path(__file__).parent.parent / "data" / "agronomy"
DATA_DIR.mkdir(parents=True, exist_ok=True)

def chunk_text(text, chunk_size=1000, overlap=200):
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunks.append(text[i:i + chunk_size])
    return chunks

def ingest_agronomy_docs():
    """Ingest PDF and TXT documents from the data/agronomy directory."""
    files = list(DATA_DIR.glob("*.pdf")) + list(DATA_DIR.glob("*.txt"))
    if not files:
        print(f"No documents found in {DATA_DIR}. Please add some agronomy PDFs or TXT files.")
        return

    for doc_path in files:
        print(f"Ingesting {doc_path.name}...")
        try:
            if doc_path.suffix.lower() == ".pdf":
                text = extract_text(doc_path)
            else:
                with open(doc_path, "r", encoding="utf-8") as f:
                    text = f.read()
                    
            chunks = chunk_text(text)
            
            ids = [str(uuid.uuid4()) for _ in chunks]
            metadatas = [{"source": doc_path.name, "chunk_index": i} for i in range(len(chunks))]
            embeddings = embed_text(chunks)
            
            agronomy_collection.add(
                ids=ids,
                documents=chunks,
                metadatas=metadatas,
                embeddings=embeddings.tolist()
            )
            print(f"Successfully ingested {len(chunks)} chunks from {doc_path.name}")
        except Exception as e:
            print(f"Error ingesting {doc_path.name}: {e}")

if __name__ == "__main__":
    ingest_agronomy_docs()
