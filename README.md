# AI Crop Price Intelligence & Forecasting System

An end-to-end Machine Learning web application for forecasting agricultural crop prices in Indian mandis (agricultural markets) using real trained **XGBoost** regression model artifacts (`xgboost_crop_price_model.pkl`), fitted feature preprocessor (`crop_price_preprocessor.pkl`), and historical mandi market data (`deployment_data.csv`).

---

## 🌟 Key Features

- **XGBoost Next-Day Price Forecasting**: Calculates exact 32 forecast-safe lag features (lags 1, 3, 7, 14, 30), rolling means/std, calendar features, coordinates, and categorical encodings to predict next-day crop prices.
- **FastAPI Backend**: Asynchronous Python REST API providing options filtering, prediction inference, historical series extraction, and cross-market analytics.
- **Modern React Dashboard**: Responsive glassmorphism interface with dynamic cascading dropdown selectors, metric cards, price trend visualizer, risk profiling, actionable trade recommendations, anomaly detection alerts, and market opportunity rankings.
- **Zero Synthetic Predictions**: Every single prediction runs through the exact trained XGBoost model and fitted preprocessor pipelines without mock fallbacks or retrain loops.

---

## 📁 Project Structure

```text
crop_price_app/
├── backend/
│   ├── main.py              # FastAPI endpoints (/health, /api/options, /api/predict, /api/history, /api/markets)
│   ├── predictor.py         # Isolated ML Predictor service, feature pipeline, & compatibility shims
│   └── requirements.txt     # Python backend dependencies
├── data/
│   └── deployment_data.csv  # 790K+ historical mandi market transaction records
├── models/
│   ├── xgboost_crop_price_model.pkl   # Trained XGBoost model artifact
│   └── crop_price_preprocessor.pkl   # Fitted scikit-learn ColumnTransformer artifact
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # React Dashboard main component
│   │   ├── index.css        # Custom glassmorphism design system & styles
│   │   └── main.jsx         # Entry point
│   ├── package.json         # Node.js dependencies
│   └── vite.config.js       # Vite configuration
├── test_backend.py          # Python test script for predictor & XGBoost pipeline
├── test_api.py              # Backend API test suite (FastAPI TestClient)
└── README.md                # Project documentation
```

---

## ⚙️ Installation & Setup

### 1. Prerequisites
- **Python**: `3.10` or higher
- **Node.js**: `v18` or higher
- **npm**: `v9` or higher

### 2. Backend Environment Setup

```bash
# Navigate to project root
cd c:/Users/priya/Downloads/crop_price_app

# Install Python backend requirements
pip install -r backend/requirements.txt
```

### 3. Frontend Environment Setup

```bash
# Navigate to frontend directory
cd frontend

# Install Node dependencies
npm install
```

---

## 🚀 Running the Application

### Start FastAPI Backend (Port 8000)

```bash
# Run from project root or backend directory
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

- API Base URL: `http://127.0.0.1:8000`
- Interactive API Docs: `http://127.0.0.1:8000/docs`

### Start React Frontend Dashboard (Port 5173)

```bash
# Run from frontend directory
cd frontend
npm run dev
```

- Dashboard URL: `http://localhost:5173`

---

## Vercel Deployment

Import this repository into Vercel and keep the project root set to the repository root (not `frontend/`). The root `pyproject.toml` selects the existing FastAPI app at `backend.main:app`, builds the React/Vite frontend, and enables Vercel's FastAPI static frontend integration. `.python-version` selects Python 3.12, and the root requirements pin scikit-learn 1.6.1 and XGBoost 1.7.6 for the existing serialized artifacts. The built frontend is served at `/`; `/health` and `/api/*` continue to use the FastAPI backend on the same origin.

Leave `VITE_API_BASE` unset for the standard single-domain deployment. Set it only when intentionally using a separately hosted API, including that API's origin and `/` if required by its routing. Local Vite development proxies `/health` and `/api` to `http://127.0.0.1:8000`.

The deployment uses the existing `models/` pickle artifacts and `data/deployment_data.csv`; no model or data fallback is configured. The Python function loads the artifacts from those project-root-relative paths at startup. Vercel may need sufficient function memory and startup duration for the 75 MB CSV and scientific Python dependencies. Review deployment build/function logs if Vercel reports a bundle, memory, or startup limit.

To test the frontend production build locally:

```bash
cd frontend
npm ci
npm run build
npm run preview
```

Run FastAPI separately on port 8000 while using Vite locally; the Vite dev and preview proxies forward API calls to it.

---

## 📡 Backend Endpoints

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/health` | `GET` | System readiness, total dataset rows, feature definitions, and date range |
| `/api/options` | `GET` | Cascading option choices (`state_name`, `district_name`, `market_center_name`, `commodity_name`, `variety`, `grade`) |
| `/api/predict` | `POST` | Accepts categorical payload, computes 32 forecast-safe features, transforms via preprocessor, predicts price with XGBoost |
| `/api/history` | `GET` | Returns historical price records for chart rendering |
| `/api/markets` | `GET` | Returns observed cross-market prices, 30d average, 7d change, rolling volatility, ranking & directional anomaly status |
| `/api/market-outlook` | `GET` | Runs the loaded XGBoost model for available market series matching a commodity, variety, and grade; returns forecast change, trend, risk, anomaly status & positive-change opportunities |

Forecast responses also include fitted-model global feature importance and signed per-prediction TreeSHAP contributions when the loaded booster can map them to the fitted preprocessor features. Explanations are omitted or marked unavailable if the model cannot provide or reconcile them; the prediction pipeline and fitted artifacts are not changed.

---

## 🧠 Prediction Feature Engineering (32 Forecast-Safe Features)

The prediction pipeline in `backend/predictor.py` constructs the exact 32 features expected by the trained model:

1. `year`, `month`, `quarter`, `day`, `day_of_week`, `day_of_year`, `week_of_year`
2. `month_sin`, `month_cos` (Cyclical month encodings)
3. `day_of_year_sin`, `day_of_year_cos` (Cyclical day-of-year encodings)
4. Lags: `lag_1`, `lag_3`, `lag_7`, `lag_14`, `lag_30`
5. Rolling Averages: `rolling_mean_3`, `rolling_mean_7`, `rolling_mean_14`, `rolling_mean_30`
6. Rolling Standard Deviations: `rolling_std_3`, `rolling_std_7`, `rolling_std_14`, `rolling_std_30`
7. Coordinates: `latitude`, `longitude`
8. Categorical Identifiers: `state_name`, `district_name`, `market_center_name`, `commodity_name`, `variety`, `grade`

---

## ✅ Verification & Test Execution

Run the backend test suite:

```bash
python test_api.py
```

Expected Output:
```text
=== TEST 1: GET /health === Status: 200
=== TEST 2: GET /api/options === Status: 200
=== TEST 3: POST /api/predict (Prediction 1) === Status: 200
=== TEST 4: POST /api/predict (Prediction 2 & 3) === Status: 200
=== TEST 5: POST /api/predict (Invalid Selection) === Status: 404
=== TEST 6: GET /api/history === Status: 200
=== TEST 7: GET /api/markets === Status: 200
ALL BACKEND API TESTS PASSED SUCCESSFULLY!
```
