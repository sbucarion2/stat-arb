import sqlite3
import statsmodels.api as sm
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller


def get_pricing(ticker, cursor):

    cursor.execute(
        """
        SELECT price_date, close
        FROM daily_prices
        WHERE ticker = '{}' AND price_date >= '2024-01-01'
        ORDER BY price_date ASC;
        """.format(ticker)
    )

    prices = cursor.fetchall()

    formatted_prices = {data[0]: data[1] for data in prices}

    return formatted_prices


def get_hedge_ratio(a, a_data, b, b_data):
    """Linear Regression, a, first ticker in pair, is x
        b is the second ticker, y. X is IV and y is DV. 
        The ratio is used the create the spread for the ticker"""
    a_constant = sm.add_constant(a_data)
    
    #Run linear regression on the pairs data for ratio
    results = sm.OLS(b_data,a_constant).fit()
    
    ratio = results.params[1] 

    return float(ratio)


connection = sqlite3.connect(r"C:\Users\sbuca\Desktop\2025-projects\stat-arb\prices.db")
cursor = connection.cursor()


cursor.execute(
    """
    SELECT ticker_a, ticker_b
    FROM ticker_pairs
    WHERE (ticker_a = 'WM' AND ticker_b ='RSG')
    """
)

garbage_pairs = cursor.fetchall()
garbage_pairs = {
    "ticker_a": garbage_pairs[0][0],
    "ticker_b": garbage_pairs[0][1],
}

garbage_pairs["ticker_a_pricing"] = get_pricing(garbage_pairs["ticker_a"], cursor)
garbage_pairs["ticker_b_pricing"] = get_pricing(garbage_pairs["ticker_b"], cursor)


hedge_ratio = get_hedge_ratio(
    garbage_pairs["ticker_a"], 
    np.array(list(garbage_pairs["ticker_a_pricing"].values())), 
    garbage_pairs["ticker_b"], 
    np.array(list(garbage_pairs["ticker_b_pricing"].values())),
)

spread = np.array(list(garbage_pairs["ticker_a_pricing"].values())) - (hedge_ratio * np.array(list(garbage_pairs["ticker_b_pricing"].values())))
normalized_spread = (spread - np.mean(spread)) / np.std(spread)


trade_data = {}
for date, price in zip(list(garbage_pairs["ticker_a_pricing"].keys()), normalized_spread):

    print(date, round(float(price), 3))

    trade_data[date] = float(price)


print("TICKER A",garbage_pairs["ticker_a"],"TICKER_B",garbage_pairs["ticker_b"],adfuller(spread)[1], hedge_ratio)
# print("\n", trade_data)

# s1 = pd.Series(garbage_pairs["ticker_a_pricing"], name=garbage_pairs["ticker_a"])
# s2 = pd.Series(garbage_pairs["ticker_b_pricing"], name=garbage_pairs["ticker_b"])

# # Combine into one DataFrame
# df = pd.concat([s1, s2], axis=1)

# # Sort by date (optional)
# df.index = pd.to_datetime(df.index)
# df = df.sort_index()

# # Export to CSV
# df.to_csv('combined_prices.csv')

cursor.close()
connection.close()