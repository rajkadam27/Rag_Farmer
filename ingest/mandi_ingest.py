"""
Mandi Historical Price Ingest Pipeline - Index 5-year price trends into vector DB.
"""
import json
import uuid
from pathlib import Path
from collections import defaultdict
from utils.chroma import mandi_trends_collection
from utils.embeddings import embed_text

DATA_PATH = Path(__file__).parent.parent / "data" / "mandi" / "historical_prices.jsonl"

MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December"
}


def ingest_mandi_trends():
    """Read historical prices and create seasonal trend summaries for RAG."""
    if not DATA_PATH.exists():
        print(f"Historical prices not found at {DATA_PATH}")
        return

    records = []
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line.strip()))

    print(f"Loaded {len(records)} historical price records.")

    # Group by commodity + APMC for trend summaries
    grouped = defaultdict(list)
    for r in records:
        key = (r["commodity"], r["apmc"])
        grouped[key].append(r)

    all_chunks = []
    all_metas = []

    for (commodity, apmc), recs in grouped.items():
        # Sort by year then month
        recs.sort(key=lambda x: (x["year"], x["month"]))

        # Create yearly summary
        yearly = defaultdict(list)
        for r in recs:
            yearly[r["year"]].append(r)

        for year, year_recs in yearly.items():
            prices = [r["avg_modal_price"] for r in year_recs]
            months = [MONTH_NAMES[r["month"]] for r in year_recs]
            peak_idx = prices.index(max(prices))
            low_idx = prices.index(min(prices))

            summary = (
                f"Historical price trend for {commodity} at {apmc} APMC in {year}: "
                f"Average modal price ranged from Rs.{min(prices)} to Rs.{max(prices)}. "
                f"Peak price of Rs.{max(prices)} was in {months[peak_idx]}. "
                f"Lowest price of Rs.{min(prices)} was in {months[low_idx]}. "
                f"Annual average: Rs.{sum(prices)//len(prices)}."
            )

            all_chunks.append(summary)
            all_metas.append({
                "commodity": commodity,
                "apmc": apmc,
                "year": str(year),
                "peak_month": months[peak_idx],
                "peak_price": str(max(prices)),
                "low_month": months[low_idx],
                "low_price": str(min(prices)),
            })

    # Also create cross-APMC comparison summaries per commodity per year
    by_commodity_year = defaultdict(list)
    for r in records:
        by_commodity_year[(r["commodity"], r["year"])].append(r)

    for (commodity, year), recs in by_commodity_year.items():
        apmc_avgs = defaultdict(list)
        for r in recs:
            apmc_avgs[r["apmc"]].append(r["avg_modal_price"])

        apmc_summary = []
        for apmc, prices in apmc_avgs.items():
            avg = sum(prices) // len(prices)
            apmc_summary.append((apmc, avg))

        apmc_summary.sort(key=lambda x: -x[1])
        best = apmc_summary[0]
        worst = apmc_summary[-1]

        text = (
            f"Cross-market comparison for {commodity} in {year}: "
            f"Best average price at {best[0]} APMC (Rs.{best[1]}), "
            f"lowest at {worst[0]} APMC (Rs.{worst[1]}). "
            f"Price difference: Rs.{best[1]-worst[1]}. "
            f"Ranking: {', '.join(f'{a} Rs.{p}' for a,p in apmc_summary)}."
        )
        all_chunks.append(text)
        all_metas.append({
            "commodity": commodity,
            "year": str(year),
            "type": "cross_market",
            "best_apmc": best[0],
            "best_price": str(best[1]),
        })

    print(f"Created {len(all_chunks)} trend summaries. Embedding...")

    # Batch embed in groups of 20 to avoid API limits
    batch_size = 20
    ids = [str(uuid.uuid4()) for _ in all_chunks]

    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i:i+batch_size]
        batch_ids = ids[i:i+batch_size]
        batch_metas = all_metas[i:i+batch_size]
        embeddings = embed_text(batch)

        mandi_trends_collection.add(
            ids=batch_ids,
            documents=batch,
            metadatas=batch_metas,
            embeddings=embeddings.tolist()
        )
        print(f"  Indexed batch {i//batch_size + 1} ({len(batch)} chunks)")

    print(f"Successfully indexed {len(all_chunks)} mandi trend chunks.")


if __name__ == "__main__":
    ingest_mandi_trends()
