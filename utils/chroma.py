import os
import json
from pathlib import Path
import numpy as np

# Persistence directory
DB_PATH = Path(__file__).parent.parent / "data" / "vector_db"
DB_PATH.mkdir(parents=True, exist_ok=True)

class LiteCollection:
    def __init__(self, name):
        self.name = name
        self.file_path = DB_PATH / f"{name}.json"
        self.data = self._load()

    def _load(self):
        if self.file_path.exists():
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"ids": [], "documents": [], "metadatas": [], "embeddings": []}

    def _save(self):
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f)

    def add(self, ids, documents, metadatas, embeddings):
        self.data["ids"].extend(ids)
        self.data["documents"].extend(documents)
        self.data["metadatas"].extend(metadatas)
        self.data["embeddings"].extend(embeddings)
        self._save()

    def query(self, query_embeddings, n_results=5, include=None):
        if not self.data["embeddings"]:
            return {"documents": [[]], "metadatas": [[]], "ids": [[]]}
        
        query_vec = np.array(query_embeddings[0])
        db_vecs = np.array(self.data["embeddings"])
        
        # Simple cosine similarity
        similarities = np.dot(db_vecs, query_vec) / (np.linalg.norm(db_vecs, axis=1) * np.linalg.norm(query_vec))
        top_indices = np.argsort(similarities)[-n_results:][::-1]
        
        return {
            "documents": [[self.data["documents"][i] for i in top_indices]],
            "metadatas": [[self.data["metadatas"][i] for i in top_indices]],
            "ids": [[self.data["ids"][i] for i in top_indices]],
            "distances": [[float(1 - similarities[i]) for i in top_indices]]
        }

# Initialise collections
agronomy_collection = LiteCollection("agronomy")
schemes_collection = LiteCollection("schemes")
gr_collection = LiteCollection("government_resolutions")
mandi_trends_collection = LiteCollection("mandi_trends")

def query_collection(collection, query_embedding, n_results=5):
    return collection.query(query_embedding, n_results=n_results)

