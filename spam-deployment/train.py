import pandas as pd
import joblib

from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB

df = pd.read_csv("spam_dataset.csv")

X = df["text"]
y = df["label"]

pipeline = Pipeline([
    ("tfidf", TfidfVectorizer()),
    ("nb", MultinomialNB())
])

pipeline.fit(X, y)

joblib.dump(pipeline, "model.joblib")

print("Model trained and saved to model.joblib")
