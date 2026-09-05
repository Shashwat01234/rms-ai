import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.utils.class_weight import compute_class_weight
from sklearn.model_selection import cross_val_score
import numpy as np
import pickle

# ── 1. Load dataset ───────────────────────────────────────────────────────────
df = pd.read_csv("queries.csv")

# Drop blank rows and duplicates
df = df.dropna(subset=["query", "category"])
df = df[df["query"].str.strip() != ""]
df = df.drop_duplicates(subset=["query"])
df = df.reset_index(drop=True)

print(f"[INFO] Loaded {len(df)} training samples across {df['category'].nunique()} categories")
print(f"[INFO] Category distribution:\n{df['category'].value_counts().to_string()}\n")

X = df["query"].str.lower().str.strip()
y = df["category"]

# ── 2. TF-IDF Vectorizer ──────────────────────────────────────────────────────
vectorizer = TfidfVectorizer(
    lowercase=True,
    stop_words="english",
    ngram_range=(1, 3),      # unigrams + bigrams + trigrams for better phrase detection
    max_features=8000,
    min_df=1,                # include even rare terms (small dataset)
    sublinear_tf=True,       # log(1+tf) scaling — reduces dominance of very common terms
)

X_vec = vectorizer.fit_transform(X)

# ── 3. Balanced Logistic Regression ──────────────────────────────────────────
classes = np.unique(y)
class_weights = compute_class_weight("balanced", classes=classes, y=y)
weight_dict   = dict(zip(classes, class_weights))

model = LogisticRegression(
    C=3.0,
    max_iter=3000,
    class_weight=weight_dict,   # balance imbalanced categories
    solver="lbfgs",
    n_jobs=-1,
)

model.fit(X_vec, y)

# ── 4. Cross-validation score ─────────────────────────────────────────────────
scores = cross_val_score(model, X_vec, y, cv=min(5, df['category'].value_counts().min()), scoring="accuracy")
print(f"[EVAL] Cross-validation accuracy: {scores.mean():.2%} ± {scores.std():.2%}")

# ── 5. Save ───────────────────────────────────────────────────────────────────
pickle.dump(model,     open("model.pkl",     "wb"))
pickle.dump(vectorizer, open("vectorizer.pkl", "wb"))

print("\n----------------------------------------")
print("[OK] Model trained and saved successfully!")
print("[OK] model.pkl and vectorizer.pkl updated.")
print("----------------------------------------\n")
