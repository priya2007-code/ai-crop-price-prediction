from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from .predictor import (
        CropPricePredictor,
        NoHistoryError,
        NotEnoughHistoryError,
        PredictorNotLoadedError,
    )
except ImportError:
    from predictor import (
        CropPricePredictor,
        NoHistoryError,
        NotEnoughHistoryError,
        PredictorNotLoadedError,
    )


app = FastAPI(title="Crop Price Prediction API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

predictor = CropPricePredictor()


class PredictionRequest(BaseModel):
    state_name: str = Field(..., min_length=1)
    district_name: str = Field(..., min_length=1)
    market_center_name: str = Field(..., min_length=1)
    commodity_name: str = Field(..., min_length=1)
    variety: str = Field(..., min_length=1)
    grade: str = Field(..., min_length=1)
    latitude: float | None = None
    longitude: float | None = None


@app.on_event("startup")
def load_predictor() -> None:
    predictor.load()


@app.get("/health")
def health() -> dict[str, Any]:
    return predictor.health()


@app.get("/api/options")
def options(
    state_name: str | None = None,
    district_name: str | None = None,
    market_center_name: str | None = None,
    commodity_name: str | None = None,
    variety: str | None = None,
    grade: str | None = None,
) -> dict[str, Any]:
    return predictor.options(
        {
            "state_name": state_name,
            "district_name": district_name,
            "market_center_name": market_center_name,
            "commodity_name": commodity_name,
            "variety": variety,
            "grade": grade,
        }
    )


@app.post("/api/predict")
def predict(request: PredictionRequest) -> dict[str, Any]:
    try:
        payload = request.model_dump() if hasattr(request, "model_dump") else request.dict()
        return predictor.predict(payload)
    except NoHistoryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (NotEnoughHistoryError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except PredictorNotLoadedError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/history")
def history(
    state_name: str | None = None,
    district_name: str | None = None,
    market_center_name: str | None = None,
    commodity_name: str | None = None,
    variety: str | None = None,
    grade: str | None = None,
    limit: int = Query(default=120, ge=1, le=1000),
) -> dict[str, Any]:
    filters = {
        "state_name": state_name,
        "district_name": district_name,
        "market_center_name": market_center_name,
        "commodity_name": commodity_name,
        "variety": variety,
        "grade": grade,
    }
    try:
        return predictor.history(filters, limit=limit)
    except NoHistoryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PredictorNotLoadedError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/markets")
def markets(
    state_name: str | None = None,
    district_name: str | None = None,
    market_center_name: str | None = None,
    commodity_name: str | None = None,
    variety: str | None = None,
    grade: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
) -> dict[str, Any]:
    filters = {
        "state_name": state_name,
        "district_name": district_name,
        "market_center_name": market_center_name,
        "commodity_name": commodity_name,
        "variety": variety,
        "grade": grade,
    }
    try:
        return predictor.markets(filters, limit=limit)
    except PredictorNotLoadedError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/market-outlook")
def market_outlook(
    commodity_name: str = Query(..., min_length=1),
    variety: str = Query(..., min_length=1),
    grade: str = Query(..., min_length=1),
    limit: int = Query(default=30, ge=1, le=100),
) -> dict[str, Any]:
    try:
        return predictor.market_outlook(
            {
                "commodity_name": commodity_name,
                "variety": variety,
                "grade": grade,
            },
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except PredictorNotLoadedError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


frontend_directory = Path(__file__).resolve().parents[1] / "frontend" / "dist"
frontend_mount = getattr(app, "frontend", None)
if callable(frontend_mount) and frontend_directory.is_dir():
    frontend_mount("/", directory=str(frontend_directory))
else:
    @app.get("/")
    def root() -> dict[str, str]:
        return {
            "message": "Crop Price Prediction API",
            "health": "/health",
            "options": "/api/options",
            "predict": "/api/predict",
            "history": "/api/history",
            "markets": "/api/markets",
            "market_outlook": "/api/market-outlook",
        }

