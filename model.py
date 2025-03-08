import os
import db
import pandas as pd
import numpy as np
from arch import arch_model

CACHE_FILE = "volatility_cache.pkl"

if __name__ == "__main__":
    if not os.path.exists(CACHE_FILE):
        print("Fetched volatility data from API and cached it.")
        db.fetch_and_cache_volatility()
    print(db.get_cached_volatility())
    
