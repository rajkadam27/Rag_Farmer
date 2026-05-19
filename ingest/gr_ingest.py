"""
GR Ingest Pipeline - Index Government Resolutions into vector DB.
"""
import json
import uuid
from pathlib import Path
from utils.chroma import gr_collection
from utils.embeddings import embed_text

DATA_PATH = Path(__file__).parent.parent / "data" / "gr" / "gr_database.jsonl"


def chunk_gr(gr: dict) -> list:
    """Create searchable text chunks from a single GR record."""
    # Main chunk: full GR context
    main = (
        f"Government Resolution {gr['gr_number']} dated {gr['date']} "
        f"by {gr['department']} Department. "
        f"Subject: {gr['subject']}. "
        f"Summary: {gr['summary']} "
        f"Beneficiaries: {gr['beneficiaries']}. "
        f"Amount/Subsidy: {gr['amount']}. "
        f"Applicable districts: {gr['districts']}."
    )
    return [main]


def ingest_grs():
    """Read GR JSONL and embed into vector DB."""
    if not DATA_PATH.exists():
        print(f"GR database not found at {DATA_PATH}")
        return

    grs = []
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                grs.append(json.loads(line.strip()))

    print(f"Found {len(grs)} government resolutions. Embedding...")

    all_chunks = []
    all_metas = []
    for gr in grs:
        chunks = chunk_gr(gr)
        for chunk in chunks:
            all_chunks.append(chunk)
            all_metas.append({
                "gr_number": gr["gr_number"],
                "date": gr["date"],
                "subject": gr["subject"],
                "department": gr["department"],
                "districts": gr["districts"],
                "amount": gr["amount"],
            })

    ids = [str(uuid.uuid4()) for _ in all_chunks]
    embeddings = embed_text(all_chunks)

    gr_collection.add(
        ids=ids,
        documents=all_chunks,
        metadatas=all_metas,
        embeddings=embeddings.tolist()
    )
    print(f"Successfully indexed {len(all_chunks)} GR chunks into vector DB.")


if __name__ == "__main__":
    ingest_grs()
