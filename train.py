import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import pickle

# ----------------------------------------
# 1. Load the dataset
# ----------------------------------------
df = pd.read_csv("queries.csv")

X = df["query"]
y = df["category"]

# ----------------------------------------
# 2. High-accuracy Smart TF-IDF
# ----------------------------------------
vectorizer = TfidfVectorizer(
    lowercase=True,
    stop_words="english",          # removes useless words (the, is, my)
    ngram_range=(1, 2),            # BIG improvement – sees patterns better
    max_features=5000              # enough for your domain
)

X_vec = vectorizer.fit_transform(X)

# ----------------------------------------
# 3. Better Logistic Regression params
# ----------------------------------------
model = LogisticRegression(
    C=2.0,                         # stronger learning
    max_iter=2000,                 # trains fully
    n_jobs=-1                      # uses all CPU cores
)

model.fit(X_vec, y)

# ----------------------------------------
# 4. Save model + vectorizer
# ----------------------------------------
pickle.dump(model, open("model.pkl", "wb"))
pickle.dump(vectorizer, open("vectorizer.pkl", "wb"))

print("\n----------------------------------------")
print("✅ High-Accuracy Model Trained Successfully!")
print("➡ model.pkl and vectorizer.pkl updated.")
print("----------------------------------------\n")


