import pandas as pd

# Sample DataFrame
data = {'col1': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]}
df = pd.DataFrame(data)

# Rolling mean with window size 3
df['rolling_mean'] = df['col1'].rolling(window=14).mean()

print(df)

df.dropna(inplace=True)

print(df)