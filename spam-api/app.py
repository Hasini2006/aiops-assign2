from fastapi import FastAPI
from pydantic import BaseModel
import joblib

app = FastAPI(title="Spam Detection API")

model = joblib.load("model.joblib")

class PredictionRequest(BaseModel):
    text: str
class PredictionResponse(BaseModel):
    label: str

@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}

@app.post("/predict", response_model=PredictionResponse)
def predict(payload: PredictionRequest) -> PredictionResponse:
    label = model.predict([payload.text])[0]
    return PredictionResponse(label=str(label))