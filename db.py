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
    Additionally, we store the first closing price for each day.
    """
    result = {
        'Date': [],
        'Volatility': [],  # Forecasted volatility from the GARCH model
        'Price': []        # Store the first price from each day's data
    }
    
    # Loop for several days (for example, last 179 days)
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
        
        # Initialize lists to store timestamps and closing prices for this day
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
        returns = df['Returns'].dropna() * 100  # Rescale returns
        
        # Fit a GARCH(1,1) model using the rescaled returns, disabling automatic rescaling
        model = arch_model(returns, vol='Garch', p=1, q=1, dist='normal', rescale=False)
        try:
            res_model = model.fit(disp='off')
            # Forecast volatility one step ahead (variance forecast is on the scaled data)
            forecast = res_model.forecast(horizon=1)
            garch_volatility_scaled = np.sqrt(forecast.variance.iloc[-1, 0])
            # Convert volatility back to original scale
            garch_volatility = garch_volatility_scaled / 100
        except Exception as e:
            print("GARCH model failed to converge:", e)
            garch_volatility = np.nan
        
        # Save the first date and price from this day's data and the computed volatility
        result['Date'].append(dates[0])
        result['Volatility'].append(garch_volatility)
        result['Price'].append(prices[0])
    
    # Cache the result dictionary to a file for future use
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(result, f)
    
    return result

def get_cached_volatility():
    """
    Check if the cache file exists.
    If yes, load and return the cached result.
    Otherwise, fetch the API data and cache the result.
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
    Compute the baseline volatility using the full 180-day period.
    
    Parameters:
        result (dict): The dictionary containing 'Date' and 'Volatility'.
    
    Returns:
        List of dictionaries with daily comparisons.
    """
    if len(result['Volatility']) < 180:
        return {"Error": "Insufficient data. Need 180 days of volatility."}
    
    baseline_mean = np.mean(result['Volatility'])
    baseline_std = np.std(result['Volatility'])
    
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

def get_zscore(target_dates):
    """
    Retrieve the average Z-score for a list of dates from the baseline comparisons.
    
    Parameters:
        target_dates (list): List of dates (in DDMMYY format) for which to compute the average Z-score.
    
    Returns:
        float: The average Z-score, rounded to one decimal place.
    """
    if not os.path.exists(CACHE_FILE):
        fetch_and_cache_volatility()
    result = get_cached_volatility()
    baseline_comparisons = compute_baseline_volatility(result)
    comparison_index = build_comparison_index(baseline_comparisons)

    # Look up comparisons for each target date
    comparisons = {date: comparison_index.get(date, None) for date in target_dates}
    # Extract valid Z-scores
    zscores = [comp["Z-score"] for comp in comparisons.values() if comp is not None and comp["Z-score"] is not None]

    if zscores:
        average_zscore = sum(zscores) / len(zscores)
        return round(average_zscore, 1)
    else:
        print("No valid Z-scores found for the selected dates.")
        return None

def refit_garch_on_cached_data():
    """
    Use the cached 180-day data (price data) to re-fit a new GARCH(1,1) model.
    This function loads the cached data, computes the daily returns from the cached prices,
    fits a new GARCH(1,1) model, and forecasts the next day's volatility.
    """
    if not os.path.exists(CACHE_FILE):
        print("Cache file not found, fetching data...")
        result = fetch_and_cache_volatility()
    else:
        with open(CACHE_FILE, "rb") as f:
            result = pickle.load(f)
    
    if 'Price' not in result or len(result['Price']) < 2:
        print("Insufficient price data in cache.")
        return None
    
    # Build a DataFrame from the cached price data and dates.
    df = pd.DataFrame({
        'Date': result['Date'],
        'Price': result['Price']
    })
    df.set_index('Date', inplace=True)
    
    # Compute daily arithmetic returns and rescale by 100
    df['Returns'] = df['Price'].pct_change().dropna() * 100
    returns = df['Returns'].dropna()
    
    model = arch_model(returns, vol='Garch', p=1, q=1, dist='normal', rescale=False)
    try:
        res_model = model.fit(disp='off')
        print("New GARCH model fitted on cached 180-day data.")
        forecast = res_model.forecast(horizon=1)
        new_volatility_scaled = np.sqrt(forecast.variance.iloc[-1, 0])
        new_volatility = new_volatility_scaled / 100
        print("Forecasted volatility from refitted model:", new_volatility)
        return res_model
    except Exception as e:
        print("Error re-fitting GARCH model on cached data:", e)
        return None
    
def update_cache_with_zscores():
    """
    Load the cached 180-day volatility data, compute baseline statistics over the period,
    calculate the z-score for each day's volatility, add these values to the cached data,
    and overwrite the cache file with the updated data.
    
    Returns:
        result (dict): Updated cache dictionary containing 'Date', 'Volatility', 'Price', and new 'Zscore'.
    """
    if not os.path.exists(CACHE_FILE):
        print("Cache file not found. Please run fetch_and_cache_volatility() first.")
        return None
    
    # Load the cached data
    with open(CACHE_FILE, "rb") as f:
        result = pickle.load(f)
    
    volatilities = result.get('Volatility', [])
    if len(volatilities) == 0:
        print("No volatility data in cache.")
        return None
    
    # Compute baseline statistics over the entire cached period (180 days)
    baseline_mean = np.mean(volatilities)
    baseline_std = np.std(volatilities)
    
    # Compute z-score for each day's volatility
    # z = (volatility - baseline_mean) / baseline_std
    zscores = [(vol - baseline_mean) / baseline_std if baseline_std != 0 else None for vol in volatilities]
    
    # Add the computed z-scores to the cache dictionary
    result['Zscore'] = zscores
    
    # Overwrite the original cache file with the updated dictionary
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(result, f)
    
    print("Cache file updated with z-scores.")
    return result

if __name__ == "__main__":
    # Ensure cache file exists (this will fetch data if needed)
    if not os.path.exists(CACHE_FILE):
        fetch_and_cache_volatility()
    
    # Optionally, re-fit the model on the cached data (if you want to refresh your volatility estimates)
    refit_garch_on_cached_data()
    
    # Now update the cache with z-scores computed from the cached volatility data.
    updated_result = update_cache_with_zscores()


