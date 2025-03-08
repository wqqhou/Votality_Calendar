import os
import pickle
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime, timedelta

CACHE_FILE = "volatility_cache.pkl"

def fetch_and_cache_volatility():
    """
    Fetch market price data and compute historical volatility for each day
    (using the sample standard deviation of returns) for several days,
    store the results in a dictionary, and cache it to a file.
    Returns the dictionary.
    """
    result = {
        'Date': [],
        'Volatility': []  # Historical volatility computed from past data.
    }
    
    all_data = []   # Store all price data (multiple per day)

    days_to_fetch = 180

    for i in range(1, days_to_fetch):       
        # Calculate the start timestamp for i days ago
        date = datetime.now().date() - timedelta(days=i)
        start_timestamp = int(datetime.combine(date, datetime.min.time()).timestamp())

        print(f"Fetching data for {i} days ago ({datetime.fromtimestamp(start_timestamp)})...")
        
        # Construct URL (make sure the startTime parameter is set correctly)
        url = (f'https://open-api-v3.coinglass.com/api/price/ohlc-history'
               f'?exchange=Binance&symbol=BTCUSDT&type=spot&interval=4h&limit=6&startTime={start_timestamp}')
        headers = {"CG-API-KEY": "b63276948277481d91ad3704def89fc8"}
        response = requests.get(url, headers=headers)
        price_history = response.json()
        
        # Parse API data
        for data_point in price_history['data']:
            dt = datetime.fromtimestamp(data_point['t']).strftime("%Y-%m-%d %H:%M")
            price = float(data_point['c'])  # Use closing price for each interval
            all_data.append([dt, price])

        time.sleep(2)  # Prevent API rate limits

    # Convert to DataFrame
    df = pd.DataFrame(all_data, columns=['DateTime', 'Price'])
    df['DateTime'] = pd.to_datetime(df['DateTime'], format="%Y-%m-%d %H:%M")
    df['Date'] = df['DateTime'].dt.date  # Extract only the date
    df.set_index('DateTime', inplace=True)

    print(f"\nTotal price points fetched: {df.shape[0]}")

    # Calculate intraday log returns
    df['Log_Returns'] = np.log(df['Price'] / df['Price'].shift(1))

    df.dropna(inplace=True)

    # Compute daily intraday volatility (standard deviation of intraday returns per day)
    daily_volatility = df.groupby('Date')['Log_Returns'].std()

    # Merge log returns and volatility to ensure alignment
    df_log_returns = df.groupby('Date')['Log_Returns'].mean().reset_index()
    df_volatility = daily_volatility.reset_index()

    # Merge to align dates
    df_combined = pd.merge(df_log_returns, df_volatility, on="Date", how="left")

    # Rename columns for clarity
    df_combined.columns = ['Date', 'Log_Returns', 'Volatility']

    df_combined.dropna(inplace=True)

    # 🔹 Store result in dictionary
    result = {
        'Date': df_combined['Date'].astype(str).tolist(),
        'Log_Returns': df_combined['Log_Returns'].tolist(),
        'Volatility': df_combined['Volatility'].tolist()
    }
    
    print(f"Computed volatility for {len(result['Date'])} days.")

    # Cache the result dictionary to a file for future use
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(result, f)

    print(f"Results stored to cache file: {CACHE_FILE}")

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

def get_volatility(date_str, result):
    """
    Retrieve the historical volatility for a given date (in DDMMYY format) from the result dictionary.
    """
    try:
        # Convert input from DDMMYY to ISO format (YYYY-MM-DD)
        dt = datetime.strptime(date_str, "%d%m%y")
        iso_date = dt.strftime("%Y-%m-%d")
    except Exception as e:
        print("Error parsing date:", e)
        return None

    # Find the matching volatility by comparing ISO date strings.
    for d, vol in zip(result['Date'], result['Volatility']):
        if d == iso_date:
            return vol
    return None  # or raise an exception if not found

def compute_baseline_volatility(result):
    """
    Compute the baseline volatility using the full available 180 days of data.
    
    Parameters:
        result (dict): The dictionary containing 'Date' and 'Volatility'.
    
    Returns:
        list: A list of dictionaries with comparison metrics for each day.
    """

    # Compute baseline statistics over the full period
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

def get_zscore(target_dates):
    """
    Retrieve the average Z-score for a list of target dates from the comparison index.
    Parameters:
        target_dates (list): List of dates in DDMMYY format.
    Returns:
        float: The average Z-score (rounded to one decimal) or None if no valid Z-scores found.
    """
    if not os.path.exists(CACHE_FILE):
        fetch_and_cache_volatility()
    result = get_cached_volatility()
    baseline_comparisons = compute_baseline_volatility(result)
    comparison_index = build_comparison_index(baseline_comparisons)

    zscores = []
    for date_str in target_dates:
        try:
            dt = datetime.strptime(date_str, "%d%m%y")
            iso_date = dt.strftime("%Y-%m-%d")
        except Exception as e:
            print(f"Error parsing date {date_str}: {e}")
            continue

        comp = comparison_index.get(iso_date)
        if comp and comp["Z-score"] is not None:
            zscores.append(comp["Z-score"])

    if zscores:
        average_zscore = sum(zscores) / len(zscores)
        return round(average_zscore, 1)
    else:
        print("No valid Z-scores found for the selected dates.")
        return None


if __name__ == "__main__":
    # Only fetch if running as the main script
    if not os.path.exists(CACHE_FILE):
        fetch_and_cache_volatility()
