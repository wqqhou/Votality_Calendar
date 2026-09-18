User can jot down events on a montly calendar, and use the past history of similar or same event to predict future volatility. 

Init (Fetching data for the past 180 days)
```
python3 db.py
```

Use the calendar to jot down events (default: 2025 March)
```
python3 crypto_c.py
```
Follow the instruction to input the date in the future when event is going to happen, then input the name/description of the event.
Finally input the date within past 180 days when a similar event happned to predict the volatility of this future event.

# Event-Based Cryptocurrency Volatility Calendar

An experimental Python application for linking scheduled events to historical Bitcoin volatility and visualizing expected event risk on a calendar.

## What it does

- Fetches 4-hour BTC/USDT spot price data and computes intraday log returns and daily realized-volatility estimates.
- Builds a 180-day historical baseline and converts daily volatility into standardized z-scores.
- Lets users enter a future event together with dates of comparable historical events; the application averages their historical volatility z-scores as an event score.
- Displays events in a desktop calendar and color-codes dates according to the combined volatility scores of scheduled events.
- Includes an experimental modeling module that compares ARCH-family volatility specifications using a time-ordered train/test split and out-of-sample error metrics.

## Methods and tools

**Python, pandas, NumPy, Tkinter, REST APIs, log returns, z-scores, ARCH/GARCH-family models, scikit-learn**

The project is an exploratory tool for combining event-based reasoning with historical market-volatility data rather than a validated trading model.

