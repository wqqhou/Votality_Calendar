import os
import db
import sys
import pandas as pd
import numpy as np
from arch import arch_model
import pickle
from sklearn.model_selection import train_test_split 
from sklearn.metrics import mean_squared_error, mean_absolute_error

def cross_validation(vol_in, p_in, q_in, o_in):
    CACHE_FILE = "volatility_cache.pkl"

    if not os.path.exists(CACHE_FILE):
        print("Fetched volatility data from API and cached it.")
        db.fetch_and_cache_volatility()

    with open(CACHE_FILE, "rb") as f:
        result = pickle.load(f)

    # Convert to DataFrame
    df = pd.DataFrame(result)

    # Ensure 'Date' is in datetime format
    df['Date'] = pd.to_datetime(df['Date'])

    # Scaling for model input

    # Debugging: Print first few rows
    print(df.head())

    # Check for missing values and drop NaNs
    df.dropna(inplace=True)

    train, test = train_test_split(df, test_size=0.2, shuffle=False)

    train_volatility = train.copy()['Volatility']
    test_volatility = test.copy()['Volatility']
    train.drop('Volatility', inplace=True, axis=1)
    test.drop('Volatility', inplace=True, axis=1)
    train.dropna(inplace=True)
    test.dropna(inplace=True)
    print(train.head())
    print(test.head())
    print(train.shape)
    print(test.shape)

    train_size = len(train)
    rolling_steps = len(test)
    rolling_df = test.copy()
    rolling_df['Log_Returns'] = pd.Series([np.nan] * len(rolling_df))
    train = pd.concat([train, rolling_df], ignore_index=True)
    rolling_forecasts = []

    for i in range(rolling_steps):

        # Define start and end indices for rolling window
        start_idx = i
        end_idx = train_size + i # Expands over time

        # Define training data (rolling window)
        train_rolling = train.iloc[start_idx:end_idx]
        if train_rolling.isna().sum().sum() > 0:
            print("NaN detected!!!")

        # Fit model
        model = arch_model(train_rolling['Log_Returns'], vol=vol_in, p=p_in, q=q_in, o=o_in, rescale=100)
        fitted_model = model.fit(disp="off", cov_type='robust')

        # Forecast
        forecast = fitted_model.forecast(horizon=1)  # Get h.1 variance

        # Get log return for the next rolling
        train.loc[train.index[end_idx], 'Log_Returns'] = forecast.mean.iloc[-1, 0]
        print(f"{train.loc[train.index[end_idx], 'Date']}: {train.loc[train.index[end_idx], 'Log_Returns']}")
        
        # Convert to volatility volatility for the next day
        rolling_forecasts.append(np.sqrt(forecast.variance.iloc[-1, 0]))


    print("\nRolling Forecasting Completed!")

    # Extract predicted volatility (square root of variance forecasts)
    test['Volatility'] = test_volatility
    test['Predicted_Volatility'] = rolling_forecasts

    print(test.head())

    # Performance Metrics
    mse = mean_squared_error(test['Volatility'], test['Predicted_Volatility'])
    mae = mean_absolute_error(test['Volatility'], test['Predicted_Volatility'])
    rmse = np.sqrt(mse)
    mape = np.mean(np.abs((test['Volatility'] - test['Predicted_Volatility']) / test['Volatility'])) * 100

    # Print Model Performance
    print("\nPerformance Metrics:")
    print(f"Mean Squared Error (MSE): {mse:.6f}")
    print(f"Mean Absolute Error (MAE): {mae:.6f}")
    print(f"Root Mean Squared Error (RMSE): {rmse:.6f}")
    print(f"Mean Absolute Percentage Error (MAPE): {mape:.2f}%")

    return mape

if __name__ == "__main__":
    vols = ['GARCH', 'ARCH', 'EGARCH', 'FIGARCH', 'APARCH', 'HARCH']
    ps = [1]
    qs = [0, 1]
    oss = [0, 1]
    min_mape = 1000
    min_vol = ''
    min_p = 0
    min_q = 0
    min_o = 0
    for vol in vols:
        for p in ps:
            for q in qs:
                for o in oss:
                    mape = cross_validation(vol, p, q, o)
                    if mape < min_mape:
                        min_mape = mape
                        min_vol = vol
                        min_p = p
                        min_q = q
                        min_o = o
    print(f"Min mape = {min_mape}, vol = {min_vol}, p = {min_p}, q = {min_q}, o = {min_o}")
