"""
FastAPI service for the spam-detection API, now with a Redis cache in front
of the model.

Loads the pre-trained scikit-learn Pipeline (TfidfVectorizer + MultinomialNB)
from model.joblib once, at import time, and exposes:
  - POST /predict   {"text": "..."} -> {"label": "spam" | "ham"}
  - GET  /healthz   -> 200 once the model is loaded

Caching (Question 2): before computing a prediction, check Redis for that
exact text. On a HIT, return the cached label without touching the model at
all. On a MISS, compute it, store it with a TTL, then return it. If Redis is
unreachable for any reason, the API silently falls back to always computing
the prediction -- caching is a performance optimization, not something that
should be able to take the whole service down.
"""

import hashlib
import os

import joblib
import redis
from fastapi import FastAPI
from pydantic import BaseModel

MODEL_PATH = "model.joblib"

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
CACHE_TTL_SECONDS = 300

app = FastAPI(title="Spam Detection API")

model = joblib.load(MODEL_PATH)

# decode_responses=True: get() returns a plain str, not bytes -- one less
# decode step at every call site. Short timeouts + retry=Retry(NoBackoff(), 0):
# redis-py 8.x otherwise retries a failed connection up to 10 times with
# exponential backoff BEFORE raising -- turning a down Redis into an ~8
# second delay on every single request despite the 1-second socket timeout.
# Zero retries means one attempt, bounded purely by socket_connect_timeout.
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=6379,  # the standard Redis port -- never actually overridden anywhere in this project
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
    retry=redis.retry.Retry(redis.backoff.NoBackoff(), 0),
)


class PredictRequest(BaseModel):
    text: str


class PredictResponse(BaseModel):
    label: str


def cache_key_for(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"predict:{digest}"


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.post("/predict", response_model=PredictResponse)
def predict(payload: PredictRequest) -> PredictResponse:
    key = cache_key_for(payload.text)

    try:
        cached_label = redis_client.get(key)
    except redis.exceptions.RedisError:
        cached_label = None

    if cached_label is not None:
        print(f"[cache HIT] {key}")
        return PredictResponse(label=cached_label)

    print(f"[cache MISS] {key}")
    label = str(model.predict([payload.text])[0])

    try:
        redis_client.setex(key, CACHE_TTL_SECONDS, label)
    except redis.exceptions.RedisError:
        pass

    return PredictResponse(label=label)