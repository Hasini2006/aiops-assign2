from fastapi import FastAPI
from pydantic import BaseModel
import joblib
import os


app = FastAPI(title="Spam Detection API")

APP_VERSION = os.environ.get("APP_VERSION", "dev")


model = joblib.load("model.joblib")


class PredictionRequest(BaseModel):
    text: str
class PredictionResponse(BaseModel):
    label: str

@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "version": APP_VERSION}


@app.post("/predict", response_model=PredictionResponse)
def predict(payload: PredictionRequest) -> PredictionResponse:
    label = model.predict([payload.text])[0]
    return PredictionResponse(label=str(label))