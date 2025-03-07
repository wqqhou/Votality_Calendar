import os
import pickle
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime
from arch import arch_model  # GARCH library

CACHE_FILE = "volatility_cache.pkl"

def fetch_and_cache_volatility():
    """
    Fetch market price data and compute volatility forecasts using a GARCH(1,1) model
    for several days, store in a dictionary, and cache it to a file.
    Returns the dictionary.
    """
    result = {
        'Date': [],
        'Volatility': []  # This will store the forecasted volatility from the GARCH model
    }
    
    # Loop for several days (for example, last 9 days)
    for i in range(1, 180):
        print(f"Fetching data for {i} days ago...")
        time.sleep(2)
        
        # Calculate the start timestamp for i days ago
        start_timestamp = int(time.time() - (i * 24 * 60 * 60))
        
        # Correct URL with '=' after startTime
        url = (f'https://open-api-v3.coinglass.com/api/price/ohlc-history'
               f'?exchange=Binance&symbol=BTCUSDT&type=spot&interval=4h&limit=6&startTime={start_timestamp}')
        headers = {"CG-API-KEY": "b63276948277481d91ad3704def89fc8"}
        response = requests.get(url, headers=headers)
        price_history = response.json()
        
        # Initialize lists to store timestamps and closing prices
        dates = []
        prices = []
        
        # Parse the API data (assuming timestamps are in seconds)
        for data_point in price_history['data']:
            # Convert timestamp to a formatted integer (e.g., DDMMYY)
            dt = int(datetime.fromtimestamp(data_point['t']).strftime("%d%m%y"))
            dates.append(dt)
            prices.append(float(data_point['c']))
        
        # Build a DataFrame from the API data
        data = {
            'Date': dates,
            'Price': prices
        }
        df = pd.DataFrame(data)
        df.set_index('Date', inplace=True)
        
        # Calculate arithmetic returns (percentage change)
        df['Returns'] = df['Price'].pct_change()
        
        # Fit a GARCH(1,1) model on the returns (drop NaN)

        # After calculating returns:
        returns = df['Returns'].dropna()

# Manually rescale the returns:
        returns_scaled = returns * 100

# Fit a GARCH(1,1) model using the rescaled returns, disabling automatic rescaling:
        model = arch_model(returns_scaled, vol='Garch', p=1, q=1, dist='normal', rescale=False)
        try:
         res = model.fit(disp='off')
    # Forecast volatility one step ahead (variance forecast is on the scaled data)
         forecast = res.forecast(horizon=1)
    # Get the forecasted volatility (standard deviation) on the scaled data:
         garch_volatility_scaled = np.sqrt(forecast.variance.iloc[-1, 0])
    # Convert volatility back to original scale:
         garch_volatility = garch_volatility_scaled / 100
        except Exception as e:
         print("GARCH model failed to converge:", e)
         garch_volatility = np.nan
        
        # Save the first date from the API result and the computed GARCH volatility for that day
        result['Date'].append(dates[0])
        result['Volatility'].append(garch_volatility)
    
    # Cache the result dictionary to a file for future use
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(result, f)
    
    return result

def get_cached_volatility():
    """
    Check if the cache file exists.
    If yes, load and return the cached result.
    Otherwise, fetch the API and cache the result.
    """
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "rb") as f:
            result = pickle.load(f)
        print("Loaded volatility data from cache.")
    else:
        result = fetch_and_cache_volatility()
        print("Fetched volatility data from API and cached it.")
    return result

def get_volatility(date, result):
    """
    Retrieve the volatility for a given date (in DDMMYY format) from the result dictionary.
    """
    for d, vol in zip(result['Date'], result['Volatility']):
        if d == date:
            return vol
    return None  # or raise an exception if the date is not found


def compute_baseline_volatility(result):
    """
    Compute the baseline volatility using all available 180 days of data.
    
    Parameters:
        result (dict): The dictionary containing 'Date' and 'Volatility'.
    
    Returns:
        dict: Contains baseline mean, std dev, and all daily comparisons.
    """
    if len(result['Volatility']) < 170:
        return {"Error": "Insufficient data. Need 180 days of volatility."}
    
    # Compute baseline statistics over the full 180-day period
    baseline_mean = np.mean(result['Volatility'])
    baseline_std = np.std(result['Volatility'])
    
    # Compute comparison metrics for each day
    comparisons = []
    for date, vol in zip(result['Date'], result['Volatility']):
        percentage_deviation = ((vol - baseline_mean) / baseline_mean) * 100 if baseline_mean != 0 else None
        z_score = (vol - baseline_mean) / baseline_std if baseline_std != 0 else None
        
        comparisons.append({
            "Date": date,
            "Actual Volatility": vol,
            "Baseline Mean": baseline_mean,
            "Baseline Std Dev": baseline_std,
            "Z-score": z_score,
            "Percentage Deviation": percentage_deviation
        })
    
    return comparisons

def build_comparison_index(baseline_comparisons):
    """
    Build a dictionary indexed by date from the baseline comparisons.
    """
    return {comp["Date"]: comp for comp in baseline_comparisons}

def get_zscore(target_date):
    """
    Retrieve the Z-score for a given date from the comparison index.
    """
    if not os.path.exists(CACHE_FILE):
        fetch_and_cache_volatility()
    result = get_cached_volatility()
    baseline_comparisons = compute_baseline_volatility(result)
    comparison_index = build_comparison_index(baseline_comparisons)

    comparisons = {date: comparison_index.get(date, None) for date in target_date}

# Extract the z-scores from the comparisons that exist and are not None:
    zscores = [comp["Z-score"] for comp in comparisons.values() if comp is not None and comp["Z-score"] is not None]

    if zscores:
        average_zscore = sum(zscores) / len(zscores)
        return round(average_zscore, 1)
    else:
        print("No valid Z-scores found for the selected dates.")


if __name__ == "__main__":
    # Only fetch if running as the main script (so importing in other files doesn't re-fetch)
    if not os.path.exists(CACHE_FILE):
        fetch_and_cache_volatility()

