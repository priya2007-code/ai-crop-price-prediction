import sys
from pathlib import Path
import pandas as pd

backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

from predictor import CropPricePredictor

def test():
    p = CropPricePredictor()
    p.load()
    print("Health:", p.health())
    
    # Pick a real series from data
    df = p.data
    grouped = df.groupby(["state_name", "district_name", "market_center_name", "commodity_name", "variety", "grade"]).size()
    valid_series = grouped[grouped >= 30].index[0]
    state, dist, mkt, comm, var, grd = valid_series
    print(f"Testing series: {state} | {dist} | {mkt} | {comm} | {var} | {grd}")
    
    payload = {
        "state_name": state,
        "district_name": dist,
        "market_center_name": mkt,
        "commodity_name": comm,
        "variety": var,
        "grade": grd
    }
    
    res = p.predict(payload)
    print("Prediction result keys:", res.keys())
    print("Prediction result:", res)

if __name__ == "__main__":
    test()
