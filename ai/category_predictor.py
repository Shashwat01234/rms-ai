from sentence_transformers import SentenceTransformer, util
import torch

# Load AI model (very light)
model = SentenceTransformer("paraphrase-MiniLM-L6-v2")

# Category definitions
CATEGORIES = {
    "Electricity": [
        "fan not working", "switch broken", "light fused", "ac not cooling",
        "socket issue", "electrical wiring problem"
    ],
    "Plumbing": [
        "water leakage", "pipe broken", "flush not working", "tap issue",
        "drain blockage"
    ],
    "Carpentry": [
        "door repair", "bed broken", "window jammed", "furniture issue"
    ],
    "Housekeeping": [
        "room cleaning", "washroom dirty", "floor not cleaned", "dusting"
    ],
    "WiFi/IT": [
        "wifi not working", "internet down", "slow network", "lan issue"
    ],
    "Mess/Food": [
        "bad food", "poor quality", "cold food", "mess complaint"
    ],
    "Security": [
        "suspicious activity", "security issue", "lost id", "theft"
    ],
    "Laundry": [
        "clothes missing", "late laundry", "laundry complaint"
    ],
    "Admin": [
        "fee issue", "room change", "documentation", "certificate request"
    ]
}

# Pre-encode descriptions
category_sentences = []
labels = []

for cat, samples in CATEGORIES.items():
    for text in samples:
        category_sentences.append(text)
        labels.append(cat)

category_embeddings = model.encode(category_sentences, convert_to_tensor=True)

def predict_category(query):
    query_embedding = model.encode(query, convert_to_tensor=True)

    # Compute cosine similarity
    similarity = util.cos_sim(query_embedding, category_embeddings)[0]

    best_idx = torch.argmax(similarity).item()
    best_score = similarity[best_idx].item()

    predicted_category = labels[best_idx]

    return {
        "category": predicted_category,
        "confidence": round(float(best_score), 3),
        "top_match": category_sentences[best_idx]
    }
