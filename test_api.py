import sys
from pathlib import Path

backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from main import app

def run_tests():
    with TestClient(app) as client:
        print("=== TEST 1: GET /health ===")
        r = client.get("/health")
        print("Status:", r.status_code)
        print("Health response:", r.json())
        assert r.status_code == 200
        assert client.get("/api/options").status_code == 200
        assert client.get("/health").json()["status"] == "ok"

        print("\n=== TEST 2: GET /api/options ===")
        r = client.get("/api/options")
        print("Status:", r.status_code)
        opts = r.json()
        print("States count:", len(opts.get("states", [])))
        print("Commodities count:", len(opts.get("commodities", [])))
        assert r.status_code == 200

        # Get valid options for selection
        states = opts.get("states", [])
        state = states[0]
        
        r_dist = client.get(f"/api/options?state_name={state}")
        districts = r_dist.json().get("districts", [])
        district = districts[0]

        r_mkt = client.get(f"/api/options?state_name={state}&district_name={district}")
        markets = r_mkt.json().get("markets", [])
        market = markets[0]

        r_comm = client.get(f"/api/options?state_name={state}&district_name={district}&market_center_name={market}")
        commodities = r_comm.json().get("commodities", [])
        commodity = commodities[0]

        r_var = client.get(f"/api/options?state_name={state}&district_name={district}&market_center_name={market}&commodity_name={commodity}")
        varieties = r_var.json().get("varieties", [])
        variety = varieties[0]

        r_grd = client.get(f"/api/options?state_name={state}&district_name={district}&market_center_name={market}&commodity_name={commodity}&variety={variety}")
        grades = r_grd.json().get("grades", [])
        grade = grades[0]

        print(f"\nSelected valid series: {state} | {district} | {market} | {commodity} | {variety} | {grade}")

        print("\n=== TEST 3: POST /api/predict (Prediction 1) ===")
        payload = {
            "state_name": state,
            "district_name": district,
            "market_center_name": market,
            "commodity_name": commodity,
            "variety": variety,
            "grade": grade
        }
        r = client.post("/api/predict", json=payload)
        print("Status:", r.status_code)
        pred1 = r.json()
        print("Prediction 1 output:", pred1)
        assert r.status_code == 200
        assert "predicted_price" in pred1
        assert "current_price" in pred1
        assert "percentage_change" in pred1
        assert "trend" in pred1
        assert pred1["trend_label"] in {"RISING", "FALLING", "STABLE"}
        assert pred1["volatility_class"] in {"Low", "Medium", "High"}
        assert pred1["recent_trend"] in {"RISING", "FALLING", "STABLE"}
        assert pred1["anomaly_status"] in {"NORMAL", "HIGH", "LOW"}
        assert "feature_importance" in pred1
        assert "feature_contributions" in pred1
        if pred1["feature_contributions"].get("available"):
            assert abs(pred1["feature_contributions"]["reconstructed_prediction"] - pred1["predicted_price"]) < 0.1
        assert "recommendation" in pred1

        print("\n=== TEST 4: POST /api/predict (Prediction 2 & 3 with other options) ===")
        all_options = client.get("/api/options").json()
        count = 0
        for s in all_options["states"][:5]:
            for c in all_options["commodities"][:5]:
                sub_opts = client.get(f"/api/options?state_name={s}&commodity_name={c}").json()
                if sub_opts["record_count"] >= 30:
                    sub_d = sub_opts["districts"][0]
                    sub_m = client.get(f"/api/options?state_name={s}&district_name={sub_d}&commodity_name={c}").json()["markets"][0]
                    sub_v = client.get(f"/api/options?state_name={s}&district_name={sub_d}&market_center_name={sub_m}&commodity_name={c}").json()["varieties"][0]
                    sub_g = client.get(f"/api/options?state_name={s}&district_name={sub_d}&market_center_name={sub_m}&commodity_name={c}&variety={sub_v}").json()["grades"][0]
                    
                    pay = {
                        "state_name": s,
                        "district_name": sub_d,
                        "market_center_name": sub_m,
                        "commodity_name": c,
                        "variety": sub_v,
                        "grade": sub_g
                    }
                    r_pred = client.post("/api/predict", json=pay)
                    if r_pred.status_code == 200:
                        count += 1
                        print(f"Prediction {count+1} ({s}, {c}):", r_pred.json())
                        if count >= 2:
                            break
            if count >= 2:
                break

        print("\n=== TEST 5: POST /api/predict (Invalid Selection Test) ===")
        invalid_payload = {
            "state_name": "NonExistentState",
            "district_name": "InvalidDistrict",
            "market_center_name": "InvalidMarket",
            "commodity_name": "FakeCrop",
            "variety": "FakeVar",
            "grade": "FAQ"
        }
        r_err = client.post("/api/predict", json=invalid_payload)
        print("Invalid payload status:", r_err.status_code)
        print("Invalid payload response:", r_err.json())
        assert r_err.status_code == 404

        print("\n=== TEST 6: GET /api/history ===")
        r_hist = client.get(f"/api/history?state_name={state}&district_name={district}&market_center_name={market}&commodity_name={commodity}&variety={variety}&grade={grade}")
        print("Status:", r_hist.status_code)
        hist_res = r_hist.json()
        print("History records returned:", hist_res.get("returned"))
        assert r_hist.status_code == 200

        print("\n=== TEST 7: GET /api/markets ===")
        r_mkts = client.get(f"/api/markets?commodity_name={commodity}")
        print("Status:", r_mkts.status_code)
        mkts_res = r_mkts.json()
        print("Markets count returned:", mkts_res.get("count"))
        if mkts_res.get("markets"):
            print("First market sample:", mkts_res["markets"][0])
            assert mkts_res["markets"][0]["anomaly_status"] in {"NORMAL", "HIGH", "LOW"}
        assert r_mkts.status_code == 200

        print("\n=== TEST 8: GET /api/market-outlook ===")
        r_outlook = client.get("/api/market-outlook", params={
            "commodity_name": commodity,
            "variety": variety,
            "grade": grade,
            "limit": 3,
        })
        print("Status:", r_outlook.status_code)
        outlook = r_outlook.json()
        print("Forecast markets returned:", outlook.get("count"))
        assert r_outlook.status_code == 200
        assert "opportunities" in outlook
        if outlook.get("markets"):
            first_outlook = outlook["markets"][0]
            for field in ("current_price", "predicted_price", "percentage_change", "trend", "risk", "volatility_class", "anomaly_status"):
                assert field in first_outlook

        print("\nALL BACKEND API TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
