from __future__ import annotations

import math
import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# Compatibility shim for unpickling scikit-learn preprocessor across versions
try:
    import sklearn.compose._column_transformer as _ct
    if not hasattr(_ct, "_RemainderColsList"):
        class _RemainderColsList(list):
            pass
        _ct._RemainderColsList = _RemainderColsList
except Exception:
    pass


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = PROJECT_ROOT / "models" / "xgboost_crop_price_model.pkl"
PREPROCESSOR_PATH = PROJECT_ROOT / "models" / "crop_price_preprocessor.pkl"
DATA_PATH = PROJECT_ROOT / "data" / "deployment_data.csv"

DATASET_COLUMNS = [
    "state_name",
    "district_name",
    "market_center_name",
    "commodity_name",
    "variety",
    "grade",
    "date",
    "modal_price",
    "latitude",
    "longitude",
]

CATEGORICAL_COLUMNS = [
    "state_name",
    "district_name",
    "market_center_name",
    "commodity_name",
    "variety",
    "grade",
]

FEATURE_COLUMNS = [
    "year",
    "month",
    "quarter",
    "day",
    "day_of_week",
    "day_of_year",
    "week_of_year",
    "month_sin",
    "month_cos",
    "day_of_year_sin",
    "day_of_year_cos",
    "lag_1",
    "lag_3",
    "lag_7",
    "lag_14",
    "lag_30",
    "rolling_mean_3",
    "rolling_mean_7",
    "rolling_mean_14",
    "rolling_mean_30",
    "rolling_std_3",
    "rolling_std_7",
    "rolling_std_14",
    "rolling_std_30",
    "latitude",
    "longitude",
    "state_name",
    "district_name",
    "market_center_name",
    "commodity_name",
    "variety",
    "grade",
]

LAG_WINDOWS = (1, 3, 7, 14, 30)
ROLLING_WINDOWS = (3, 7, 14, 30)
MIN_HISTORY_ROWS = max(max(LAG_WINDOWS), max(ROLLING_WINDOWS))


class PredictorError(Exception):
    """Base class for prediction-service errors."""


class PredictorNotLoadedError(PredictorError):
    """Raised when the predictor is used before loading artifacts."""


class NoHistoryError(PredictorError):
    """Raised when no matching historical series exists."""


class NotEnoughHistoryError(PredictorError):
    """Raised when a matching series is too short for forecast features."""


class CropPricePredictor:
    def __init__(
        self,
        model_path: Path = MODEL_PATH,
        preprocessor_path: Path = PREPROCESSOR_PATH,
        data_path: Path = DATA_PATH,
    ) -> None:
        self.model_path = Path(model_path)
        self.preprocessor_path = Path(preprocessor_path)
        self.data_path = Path(data_path)
        self.model: Any | None = None
        self.preprocessor: Any | None = None
        self.data: pd.DataFrame | None = None
        self.model_input_features: int | None = None
        self.loaded = False

    def load(self) -> None:
        with self.preprocessor_path.open("rb") as file:
            self.preprocessor = pickle.load(file)

        with self.model_path.open("rb") as file:
            self.model = pickle.load(file)
            self._patch_model_compatibility()

        data = pd.read_csv(self.data_path)
        missing_columns = [col for col in DATASET_COLUMNS if col not in data.columns]
        if missing_columns:
            raise ValueError(f"deployment_data.csv is missing columns: {missing_columns}")

        data = data[DATASET_COLUMNS].copy()
        data["date"] = pd.to_datetime(data["date"], errors="raise")
        data["modal_price"] = pd.to_numeric(data["modal_price"], errors="raise")
        data["latitude"] = pd.to_numeric(data["latitude"], errors="coerce")
        data["longitude"] = pd.to_numeric(data["longitude"], errors="coerce")
        data = data.sort_values(["date", *CATEGORICAL_COLUMNS]).reset_index(drop=True)

        self.data = data
        self._validate_preprocessor()
        self.model_input_features = self._resolve_model_input_features()
        self.loaded = True

    def _patch_model_compatibility(self) -> None:
        if self.model is None:
            return
        import inspect
        try:
            missing_params = set()
            for cls in self.model.__class__.__mro__:
                if hasattr(cls, "__init__"):
                    try:
                        missing_params.update(inspect.signature(cls.__init__).parameters.keys())
                    except Exception:
                        pass
            for param in missing_params:
                if param not in ("self", "kwargs") and not hasattr(self.model, param):
                    setattr(self.model, param, None)
        except Exception:
            pass

    def health(self) -> dict[str, Any]:
        if not self.loaded or self.data is None:
            return {
                "status": "not_loaded",
                "model_path": str(self.model_path),
                "preprocessor_path": str(self.preprocessor_path),
                "data_path": str(self.data_path),
            }

        return {
            "status": "ok",
            "rows": int(len(self.data)),
            "dataset_columns": DATASET_COLUMNS,
            "required_prediction_features": FEATURE_COLUMNS,
            "raw_input_feature_count": len(FEATURE_COLUMNS),
            "model_input_feature_count": self.model_input_features,
            "date_min": self.data["date"].min().date().isoformat(),
            "date_max": self.data["date"].max().date().isoformat(),
        }

    def options(self, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        self._ensure_loaded()
        assert self.data is not None

        frame = self._filter_frame(self.data, filters or {})
        return {
            "record_count": int(len(frame)),
            "states": self._unique_values(frame, "state_name"),
            "districts": self._unique_values(frame, "district_name"),
            "markets": self._unique_values(frame, "market_center_name"),
            "commodities": self._unique_values(frame, "commodity_name"),
            "varieties": self._unique_values(frame, "variety"),
            "grades": self._unique_values(frame, "grade"),
        }

    def history(self, filters: dict[str, Any], limit: int = 120) -> dict[str, Any]:
        self._ensure_loaded()
        assert self.data is not None

        frame = self._filter_frame(self.data, filters).sort_values("date")
        if frame.empty:
            raise NoHistoryError("No history found for the selected filters.")

        total_rows = int(len(frame))
        limited = frame.tail(limit) if limit else frame
        return {
            "count": total_rows,
            "returned": int(len(limited)),
            "history": [self._history_record(row) for _, row in limited.iterrows()],
        }

    def predict(self, payload: dict[str, Any], include_explanations: bool = True) -> dict[str, Any]:
        self._ensure_loaded()
        assert self.model is not None
        assert self.preprocessor is not None

        selection = self._selection_from_payload(payload)
        history = self._series_history(selection)
        features, forecast_date = self._forecast_features(
            history=history,
            selection=selection,
            latitude_override=payload.get("latitude"),
            longitude_override=payload.get("longitude"),
        )

        feature_frame = pd.DataFrame([features], columns=FEATURE_COLUMNS)
        transformed = self.preprocessor.transform(feature_frame)
        prediction = self.model.predict(transformed)
        predicted_price = float(np.asarray(prediction).ravel()[0])
        current_price = float(history["modal_price"].iloc[-1])
        feature_importance = self._feature_importance(transformed) if include_explanations else None
        feature_contributions = self._prediction_contributions(transformed, predicted_price) if include_explanations else None

        abs_change = round(predicted_price - current_price, 2)
        pct_change = round((abs_change / current_price) * 100.0, 2) if current_price != 0 else 0.0

        # Calculate historical volatility (30-day CV percentage)
        recent_prices = history["modal_price"].tail(30).astype(float)
        std_30 = float(recent_prices.std(ddof=1)) if len(recent_prices) > 1 else 0.0
        mean_30 = float(recent_prices.mean()) if len(recent_prices) > 0 else current_price
        volatility_pct = round((std_30 / mean_30) * 100.0, 2) if mean_30 != 0 else 0.0
        anomaly_status, anomaly_mean, anomaly_std = self._price_anomaly_status(
            history["modal_price"].iloc[:-1].tail(30), current_price
        )

        # Trend definition
        if pct_change > 0.5:
            trend = "Bullish"
        elif pct_change < -0.5:
            trend = "Bearish"
        else:
            trend = "Neutral"

        # Risk level based on volatility and magnitude of change
        if volatility_pct > 8.0 or abs(pct_change) > 8.0:
            risk = "High"
        elif volatility_pct > 3.0 or abs(pct_change) > 3.0:
            risk = "Medium"
        else:
            risk = "Low"

        if volatility_pct > 8.0:
            volatility_class = "High"
        elif volatility_pct > 3.0:
            volatility_class = "Medium"
        else:
            volatility_class = "Low"

        recent_prices = history["modal_price"].tail(7).astype(float)
        prior_price = float(history["modal_price"].iloc[-8]) if len(history) > 7 else float(history["modal_price"].iloc[0])
        recent_change = ((float(recent_prices.iloc[-1]) - prior_price) / prior_price * 100.0) if prior_price else 0.0
        recent_trend = "RISING" if recent_change > 0.5 else "FALLING" if recent_change < -0.5 else "STABLE"
        trend_label = "RISING" if pct_change > 0.5 else "FALLING" if pct_change < -0.5 else "STABLE"

        # Recommendation logic
        if pct_change >= 2.0:
            recommendation = "Buy / Hold Stock - Strong upward movement predicted"
        elif pct_change >= 0.5:
            recommendation = "Hold - Mild upward trend expected"
        elif pct_change <= -2.0:
            recommendation = "Sell / Liquidate - Downward price pressure forecasted"
        elif pct_change <= -0.5:
            recommendation = "Caution - Slight decline expected, limit exposure"
        else:
            recommendation = "Hold / Neutral - Market stable with minimal fluctuation"

        anomaly_note = (
            f"Verify locally before acting: the latest price is a {anomaly_status.lower()} anomaly. "
            if anomaly_status != "NORMAL"
            else ""
        )
        decision_recommendation = (
            f"{anomaly_note}{trend_label} outlook ({pct_change:+.2f}%) with {risk.lower()} risk and "
            f"{volatility_class.lower()} volatility ({volatility_pct:.2f}% over 30 observations)."
        )

        result = {
            "current_price": round(current_price, 2),
            "predicted_price": round(predicted_price, 2),
            "absolute_change": abs_change,
            "percentage_change": pct_change,
            "trend": trend,
            "trend_label": trend_label,
            "volatility": f"{volatility_pct}%",
            "volatility_value": volatility_pct,
            "volatility_class": volatility_class,
            "recent_trend": recent_trend,
            "recent_change_7_records_pct": round(recent_change, 2),
            "risk": risk,
            "recommendation": recommendation,
            "decision_support": {
                "recommendation": decision_recommendation,
                "anomaly_status": anomaly_status,
                "anomaly_baseline_mean": round(anomaly_mean, 2),
                "anomaly_baseline_std": round(anomaly_std, 2),
                "anomaly_method": "latest price vs preceding 30 observations; outside 2 standard deviations",
            },
            "anomaly_status": anomaly_status,
            "anomaly_baseline_mean": round(anomaly_mean, 2),
            "forecast_date": forecast_date.date().isoformat(),

            # Additional detailed metrics for compatibility
            "prediction": round(predicted_price, 2),
            "last_observed_date": history["date"].iloc[-1].date().isoformat(),
            "last_observed_price": round(current_price, 2),
            "history_rows_used": int(len(history)),
            "features": self._json_safe_record(features),
        }
        if include_explanations:
            result["feature_importance"] = feature_importance
            result["feature_contributions"] = feature_contributions
        return result

    def _feature_importance(self, transformed: Any, top_n: int = 8) -> dict[str, Any]:
        assert self.model is not None
        assert self.preprocessor is not None

        importances = getattr(self.model, "feature_importances_", None)
        if importances is None:
            return {"available": False, "reason": "The loaded XGBoost model does not expose feature_importances_."}

        try:
            names = list(self.preprocessor.get_feature_names_out())
            values = np.asarray(importances, dtype=float).ravel()
            transformed_values = transformed.toarray() if hasattr(transformed, "toarray") else transformed
            observed_values = np.asarray(transformed_values, dtype=float).ravel()
        except (AttributeError, TypeError, ValueError) as exc:
            return {"available": False, "reason": f"Feature importance could not be mapped to fitted input names: {exc}"}

        if len(names) != len(values) or len(observed_values) != len(values):
            return {"available": False, "reason": "Fitted feature names and XGBoost input dimensions do not match."}

        total_importance = float(values.sum())
        if total_importance <= 0:
            return {"available": False, "reason": "The loaded model reports no non-zero feature importance."}

        ranked_indices = np.argsort(values)[::-1]
        factors = []
        for index in ranked_indices:
            importance = float(values[index])
            if importance <= 0 or len(factors) >= top_n:
                continue
            name = str(names[index])
            for prefix in ("numeric__", "categorical__", "num__", "cat__"):
                if name.startswith(prefix):
                    name = name[len(prefix):]
                    break
            factors.append({
                "feature": name,
                "importance_pct": round(importance / total_importance * 100.0, 2),
                "model_input_value": round(float(observed_values[index]), 6),
            })

        return {
            "available": bool(factors),
            "source": "XGBoost feature_importances_",
            "scope": "global model importance; values are not signed local contributions",
            "factors": factors,
        }

    def _prediction_contributions(self, transformed: Any, predicted_price: float, top_n: int = 6) -> dict[str, Any]:
        assert self.model is not None
        assert self.preprocessor is not None

        get_booster = getattr(self.model, "get_booster", None)
        if not callable(get_booster):
            return {"available": False, "reason": "The loaded estimator does not expose an XGBoost booster."}

        try:
            import xgboost as xgb

            booster = get_booster()
            contributions = np.asarray(
                booster.predict(xgb.DMatrix(transformed), pred_contribs=True),
                dtype=float,
            ).reshape(-1)
            names = list(self.preprocessor.get_feature_names_out())
        except (AttributeError, TypeError, ValueError, xgb.core.XGBoostError) as exc:
            return {"available": False, "reason": f"The loaded booster could not calculate prediction contributions: {exc}"}

        if len(contributions) != len(names) + 1:
            return {"available": False, "reason": "XGBoost contribution width does not match fitted feature names."}

        ranked_indices = np.argsort(np.abs(contributions[:-1]))[::-1]
        factors = []
        for index in ranked_indices:
            contribution = float(contributions[index])
            if abs(contribution) < 1e-9 or len(factors) >= top_n:
                continue
            name = str(names[index])
            for prefix in ("numeric__", "categorical__", "num__", "cat__"):
                if name.startswith(prefix):
                    name = name[len(prefix):]
                    break
            factors.append({
                "feature": name,
                "contribution": round(contribution, 2),
                "direction": "raises" if contribution > 0 else "lowers",
            })

        base_value = float(contributions[-1])
        reconstructed = float(contributions.sum())
        tolerance = max(0.05, abs(predicted_price) * 1e-4)
        if abs(reconstructed - predicted_price) > tolerance:
            return {"available": False, "reason": "TreeSHAP contributions did not reconcile with the fitted model prediction."}

        return {
            "available": bool(factors),
            "source": "XGBoost pred_contribs (TreeSHAP)",
            "base_value": round(base_value, 2),
            "reconstructed_prediction": round(reconstructed, 2),
            "factors": factors,
        }

    def markets(self, filters: dict[str, Any], limit: int = 50) -> dict[str, Any]:
        self._ensure_loaded()
        assert self.data is not None

        frame = self._filter_frame(self.data, filters)
        if frame.empty:
            return {"count": 0, "markets": []}

        # Group by market center to compute comparison analytics
        group_cols = ["state_name", "district_name", "market_center_name"]
        if "commodity_name" in filters and filters["commodity_name"]:
            group_cols.append("commodity_name")

        markets_list = []
        for keys, grp in frame.groupby(group_cols):
            grp_sorted = grp.sort_values("date")
            latest_row = grp_sorted.iloc[-1]
            prices = grp_sorted["modal_price"].tail(30).astype(float)
            
            latest_p = float(latest_row["modal_price"])
            mean_p = float(prices.mean())
            std_p = float(prices.std(ddof=1)) if len(prices) > 1 else 0.0
            
            anomaly_status, _, _ = self._price_anomaly_status(
                grp_sorted["modal_price"].iloc[:-1].tail(30), latest_p
            )
            
            # Price change 7 days ago if available
            p_7d_ago = float(grp_sorted["modal_price"].iloc[-7]) if len(grp_sorted) >= 7 else float(grp_sorted["modal_price"].iloc[0])
            chg_7d = round(latest_p - p_7d_ago, 2)
            pct_7d = round((chg_7d / p_7d_ago) * 100.0, 2) if p_7d_ago != 0 else 0.0

            state_val = grp_sorted["state_name"].iloc[-1]
            dist_val = grp_sorted["district_name"].iloc[-1]
            mkt_val = grp_sorted["market_center_name"].iloc[-1]
            comm_val = grp_sorted["commodity_name"].iloc[-1] if "commodity_name" in grp_sorted.columns else ""

            markets_list.append({
                "state_name": state_val,
                "district_name": dist_val,
                "market_center_name": mkt_val,
                "commodity_name": comm_val,
                "latitude": self._json_safe_value(latest_row.get("latitude")),
                "longitude": self._json_safe_value(latest_row.get("longitude")),
                "latest_date": latest_row["date"].date().isoformat(),
                "latest_price": round(latest_p, 2),
                "avg_price_30d": round(mean_p, 2),
                "change_7d": chg_7d,
                "pct_change_7d": pct_7d,
                "volatility_30d": round((std_p / mean_p * 100.0) if mean_p != 0 else 0.0, 2),
                "is_anomaly": anomaly_status != "NORMAL",
                "anomaly_status": anomaly_status,
                "record_count": int(len(grp)),
            })

        # Sort by latest_price descending for opportunity ranking
        markets_list.sort(key=lambda x: x["latest_price"], reverse=True)
        for rank, item in enumerate(markets_list, 1):
            item["opportunity_rank"] = rank

        return {
            "count": len(markets_list),
            "markets": markets_list[:limit]
        }

    def market_outlook(self, filters: dict[str, Any], limit: int = 30) -> dict[str, Any]:
        self._ensure_loaded()
        required = ("commodity_name", "variety", "grade")
        missing = [column for column in required if not filters.get(column)]
        if missing:
            raise ValueError(f"Market forecasts require these filters: {missing}")

        market_data = self.markets(filters, limit=limit)
        comparisons = []
        skipped = 0
        for market in market_data["markets"]:
            payload = {
                **filters,
                "state_name": market["state_name"],
                "district_name": market["district_name"],
                "market_center_name": market["market_center_name"],
                "commodity_name": filters["commodity_name"],
                "variety": filters["variety"],
                "grade": filters["grade"],
            }
            try:
                forecast = self.predict(payload, include_explanations=False)
            except (NoHistoryError, NotEnoughHistoryError, ValueError):
                skipped += 1
                continue

            comparisons.append({
                **market,
                "current_price": forecast["current_price"],
                "predicted_price": forecast["predicted_price"],
                "absolute_change": forecast["absolute_change"],
                "percentage_change": forecast["percentage_change"],
                "trend": forecast["trend_label"],
                "risk": forecast["risk"],
                "volatility": forecast["volatility"],
                "volatility_value": forecast["volatility_value"],
                "volatility_class": forecast["volatility_class"],
                "forecast_date": forecast["forecast_date"],
            })

        comparisons.sort(key=lambda item: item["percentage_change"], reverse=True)
        for rank, item in enumerate(comparisons, 1):
            item["opportunity_rank"] = rank

        return {
            "count": len(comparisons),
            "skipped_insufficient_history": skipped,
            "markets": comparisons,
            "opportunities": [item for item in comparisons if item["percentage_change"] > 0][:5],
        }

    def _ensure_loaded(self) -> None:
        if not self.loaded or self.model is None or self.preprocessor is None or self.data is None:
            raise PredictorNotLoadedError("Predictor artifacts have not been loaded.")

    def _price_anomaly_status(self, baseline: Any, latest_price: float) -> tuple[str, float, float]:
        values = pd.Series(baseline, dtype=float).dropna()
        if len(values) < 2:
            return "NORMAL", float(values.mean()) if len(values) else 0.0, 0.0

        mean_price = float(values.mean())
        std_price = float(values.std(ddof=1))
        if std_price > 0 and latest_price > mean_price + (2.0 * std_price):
            status = "HIGH"
        elif std_price > 0 and latest_price < mean_price - (2.0 * std_price):
            status = "LOW"
        else:
            status = "NORMAL"
        return status, mean_price, std_price

    def _validate_preprocessor(self) -> None:
        assert self.preprocessor is not None

        n_features = getattr(self.preprocessor, "n_features_in_", None)
        if n_features != len(FEATURE_COLUMNS):
            raise ValueError(
                f"Preprocessor expects {n_features} raw features; "
                f"backend builds {len(FEATURE_COLUMNS)}."
            )

        feature_names = list(getattr(self.preprocessor, "feature_names_in_", []))
        if feature_names != FEATURE_COLUMNS:
            raise ValueError(
                "Preprocessor feature order does not match backend FEATURE_COLUMNS."
            )

    def _resolve_model_input_features(self) -> int | None:
        assert self.preprocessor is not None

        preprocessor_width = self._preprocessor_output_width()
        model_width = self._model_feature_count()
        if preprocessor_width and model_width and preprocessor_width != model_width:
            raise ValueError(
                f"Preprocessor outputs {preprocessor_width} features, "
                f"but model expects {model_width}."
            )

        return model_width or preprocessor_width

    def _preprocessor_output_width(self) -> int | None:
        output_indices = getattr(self.preprocessor, "output_indices_", None)
        if not output_indices:
            return None

        stops = [
            value.stop
            for value in output_indices.values()
            if isinstance(value, slice) and value.stop is not None
        ]
        return max(stops) if stops else None

    def _model_feature_count(self) -> int | None:
        if self.model is None:
            return None

        get_booster = getattr(self.model, "get_booster", None)
        if not callable(get_booster):
            return None

        booster = get_booster()
        num_features = getattr(booster, "num_features", None)
        return int(num_features()) if callable(num_features) else None

    def _selection_from_payload(self, payload: dict[str, Any]) -> dict[str, str]:
        selection: dict[str, str] = {}
        missing: list[str] = []
        for column in CATEGORICAL_COLUMNS:
            value = payload.get(column)
            if value is None or str(value).strip() == "":
                missing.append(column)
            else:
                selection[column] = str(value).strip()

        if missing:
            raise ValueError(f"Missing required prediction fields: {missing}")

        return selection

    def _series_history(self, selection: dict[str, str]) -> pd.DataFrame:
        assert self.data is not None

        history = self._filter_frame(self.data, selection)
        history = history.dropna(subset=["modal_price"]).sort_values("date")
        if history.empty:
            raise NoHistoryError("No price history found for the selected series.")

        if len(history) < MIN_HISTORY_ROWS:
            raise NotEnoughHistoryError(
                f"At least {MIN_HISTORY_ROWS} history rows are required; "
                f"found {len(history)}."
            )

        return history.reset_index(drop=True)

    def _forecast_features(
        self,
        history: pd.DataFrame,
        selection: dict[str, str],
        latitude_override: Any = None,
        longitude_override: Any = None,
    ) -> tuple[dict[str, Any], pd.Timestamp]:
        last_date = history["date"].iloc[-1]
        forecast_date = last_date + pd.Timedelta(days=1)
        prices = history["modal_price"].astype(float)

        day_of_year = int(forecast_date.dayofyear)
        month = int(forecast_date.month)
        features: dict[str, Any] = {
            "year": int(forecast_date.year),
            "month": month,
            "quarter": int(forecast_date.quarter),
            "day": int(forecast_date.day),
            "day_of_week": int(forecast_date.dayofweek),
            "day_of_year": day_of_year,
            "week_of_year": int(forecast_date.isocalendar().week),
            "month_sin": math.sin(2.0 * math.pi * month / 12.0),
            "month_cos": math.cos(2.0 * math.pi * month / 12.0),
            "day_of_year_sin": math.sin(2.0 * math.pi * day_of_year / 365.0),
            "day_of_year_cos": math.cos(2.0 * math.pi * day_of_year / 365.0),
        }

        for window in LAG_WINDOWS:
            features[f"lag_{window}"] = float(prices.iloc[-window])

        for window in ROLLING_WINDOWS:
            rolling_values = prices.iloc[-window:]
            features[f"rolling_mean_{window}"] = float(rolling_values.mean())
            features[f"rolling_std_{window}"] = float(rolling_values.std(ddof=1))

        features["latitude"] = self._coordinate_value(
            history=history,
            column="latitude",
            override=latitude_override,
        )
        features["longitude"] = self._coordinate_value(
            history=history,
            column="longitude",
            override=longitude_override,
        )
        features.update(selection)

        return {column: features[column] for column in FEATURE_COLUMNS}, forecast_date

    def _coordinate_value(self, history: pd.DataFrame, column: str, override: Any) -> float:
        override_value = self._optional_float(override)
        if override_value is not None:
            return override_value

        valid_values = history[column].dropna()
        if valid_values.empty:
            return float("nan")

        return float(valid_values.iloc[-1])

    def _filter_frame(self, frame: pd.DataFrame, filters: dict[str, Any]) -> pd.DataFrame:
        filtered = frame
        for column, raw_value in filters.items():
            if column not in DATASET_COLUMNS:
                continue
            if raw_value is None or str(raw_value).strip() == "":
                continue
            filtered = filtered[filtered[column] == str(raw_value).strip()]
        return filtered

    def _unique_values(self, frame: pd.DataFrame, column: str) -> list[Any]:
        values = frame[column].dropna().unique().tolist()
        return sorted(self._json_safe_value(value) for value in values)

    def _history_record(self, row: pd.Series) -> dict[str, Any]:
        record = {column: self._json_safe_value(row[column]) for column in DATASET_COLUMNS}
        record["date"] = row["date"].date().isoformat()
        return record

    def _json_safe_record(self, record: dict[str, Any]) -> dict[str, Any]:
        return {key: self._json_safe_value(value) for key, value in record.items()}

    def _json_safe_value(self, value: Any) -> Any:
        if isinstance(value, pd.Timestamp):
            return value.date().isoformat()
        if isinstance(value, np.generic):
            value = value.item()
        if isinstance(value, float) and math.isnan(value):
            return None
        return value

    def _optional_float(self, value: Any) -> float | None:
        if value is None or value == "":
            return None
        numeric_value = float(value)
        return None if math.isnan(numeric_value) else numeric_value

