import pandas as pd
import joblib

from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB


# Load the dataset
df = pd.read_csv("spam_dataset.csv")

# Input and target
X = df["text"]
y = df["label"]

# Create the ML pipeline
pipeline = Pipeline([
    ("tfidf", TfidfVectorizer()),
    ("nb", MultinomialNB())
])

# Train the model
pipeline.fit(X, y)

# Save the complete pipeline
joblib.dump(pipeline, "model.joblib")

print("Model trained and saved to model.joblib")
