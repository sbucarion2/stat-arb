import sqlite3
import statsmodels.api as sm
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller
from datetime import datetime, timedelta



def get_trading_dates(today, cursor):

    cursor.execute(
        """
        SELECT DISTINCT(price_date)
        FROM daily_prices
        WHERE price_date <= '{}'
        ORDER BY price_date ASC
        """.format(today)
    )

    dates = cursor.fetchall()

    return [date[0] for date in dates]


def get_single_pair(ticker_a, ticker_b, cursor):

    cursor.execute(
        """
        SELECT ticker_a, ticker_b
        FROM ticker_pairs
        WHERE (ticker_a = '{}' AND ticker_b ='{}')
        """.format(ticker_a, ticker_b)
    )

    pairs = cursor.fetchall()

    return pairs[0][0], pairs[0][1]


def get_pricing(ticker, start_date, end_date, cursor):

    cursor.execute(
        """
        SELECT price_date, close
        FROM daily_prices
        WHERE ticker = '{}' 
            AND (price_date >= '{}' AND price_date <= '{}')
        ORDER BY price_date ASC;
        """.format(ticker, start_date, end_date)
    )

    prices = cursor.fetchall()

    formatted_prices = {data[0]: data[1] for data in prices}

    return formatted_prices


def get_hedge_ratio(a_data, b_data):
    """Linear Regression, a, first ticker in pair, is x
        b is the second ticker, y. X is IV and y is DV. 
        The ratio is used the create the spread for the ticker"""
    a_constant = sm.add_constant(a_data)
    
    #Run linear regression on the pairs data for ratio
    results = sm.OLS(b_data,a_constant).fit()
    
    ratio = results.params[1] 

    return float(ratio)


def calculate_spread(a_pricing, b_pricing, hedge_ratio):
    """returns normalized spread of B - (hr*A)"""

    spread = {}
    for price_date in a_pricing.keys():

        spread_point = b_pricing[price_date] - (a_pricing[price_date] * hedge_ratio)

        spread[price_date] = spread_point

    spread_mean = np.mean(list(spread.values()))
    spread_std = np.std(list(spread.values()))

    normalized_spread = {}
    for price_date, price in spread.items():

        normalized_spread[price_date] = round(float(((price - spread_mean) / spread_std)), 4)

    return normalized_spread


def get_halflife(spread):
    """Regression on the pairs spread to find lookback
        period for trading"""
    x_lag = np.roll(spread,1)
    x_lag[0] = 0
    y_ret = spread - x_lag
    y_ret[0] = 0
    
    x_lag_constant = sm.add_constant(x_lag)
    
    res = sm.OLS(y_ret,x_lag_constant).fit()
    halflife = -np.log(2) / res.params[1]
    halflife = int(round(halflife))

    return halflife


def save_data_to_excel(ticker_a_trading_pricing, ticker_b_trading_pricing):
    
    s1 = pd.Series(ticker_a_trading_pricing, name="QQQ")
    s2 = pd.Series(ticker_b_trading_pricing, name="TQQQ")

    # Combine into one DataFrame
    df = pd.concat([s1, s2], axis=1)

    # Sort by date (optional)
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    # Export to CSV
    df.to_csv('combined_prices.csv')


def check_stationarity(ticker_a, ticker_b, trading_dates, cursor):

    test_date_range = trading_dates[((-252*3)-100):-100]

    ticker_a_testing_pricing = get_pricing(
        ticker_a, 
        test_date_range[0], 
        test_date_range[-1], 
        cursor
    )
    ticker_b_testing_pricing = get_pricing(
        ticker_b, 
        test_date_range[0], 
        test_date_range[-1], 
        cursor
    )

    hedge_ratio = get_hedge_ratio(
        list(ticker_a_testing_pricing.values()), 
        list(ticker_b_testing_pricing.values())
    )

    spread = calculate_spread(
        ticker_a_testing_pricing, 
        ticker_b_testing_pricing, 
        hedge_ratio
    )

    adfuller_pvalue = adfuller(list(spread.values()))[1]

    if adfuller_pvalue <= 0.05:

        print("Stationary", test_date_range[-1], adfuller_pvalue)

        halflife = get_halflife(list(spread.values()))

        return True, hedge_ratio, halflife

    else:

        print("Not Stationary:", adfuller_pvalue)

        return False, 0, 0


def get_trade_signal(ticker_a, ticker_b, trading_dates, halflife, hedge_ratio, today, cursor):

    trading_date_range = trading_dates[-100:]

    ticker_a_trading_pricing = get_pricing(
        ticker_a, 
        trading_date_range[-halflife], 
        trading_date_range[-1], 
        cursor
    )
    ticker_b_trading_pricing = get_pricing(
        ticker_b, 
        trading_date_range[-halflife], 
        trading_date_range[-1], 
        cursor
    )

    trading_spread = calculate_spread(
        ticker_a_trading_pricing, 
        ticker_b_trading_pricing, 
        hedge_ratio
    )

    STD_THRESHOLD = 1.5
    if trading_spread[today] >= STD_THRESHOLD and list(trading_spread.items())[-2][1] <= STD_THRESHOLD:

        # if spread is above +threshold, B ticker has gotten much bigger or A ticker has gotten much smaller
        # Short B to bring down value and long A to bring up value

        print("Trade!", today, trading_spread[today], list(trading_spread.items())[-2])

        print(
            "BUY {} {} @ {} - SELL 1 {} @ {} on {}".format(
                round(hedge_ratio, 3), 
                ticker_a, 
                ticker_a_trading_pricing[today],
                ticker_b, 
                ticker_b_trading_pricing[today],
                today,
            )
        )


def main(today: str):

    connection = sqlite3.connect(r"C:\Users\sbuca\Desktop\2025-projects\stat-arb\prices.db")
    cursor = connection.cursor()

    trading_dates = get_trading_dates(today, cursor)

    # print(test_date_range[-1], trading_date_range[0])

    ticker_a, ticker_b = get_single_pair("QQQ", "TQQQ", cursor)

    is_stationary, hedge_ratio, halflife = check_stationarity(ticker_a, ticker_b, trading_dates, cursor)

    if is_stationary is False:

        return {}

    # print("TESTING PAIRS:\n    TICKER A: {} \n    TICKER B: {}".format(ticker_a, ticker_b))

    # print("TESTING PERIOD:\n     {} TO {}".format(test_date_range[0], test_date_range[-1]))

    # print("PAIRS DATA:\n     HEDGE RATIO: {}\n     ADF-P: {}".format(hedge_ratio, adfuller_pvalue))

    # print("PAIRS DATA:\n     HEDGE RATIO: {}\n     ADF-P: {}\n     HALFLIFE: {}".format(hedge_ratio, adfuller_pvalue, halflife))

    # Now using HL make spread with the past 32 trading days

    trade_signal = get_trade_signal(ticker_a, ticker_b, trading_dates, halflife, hedge_ratio, today, cursor)


    # save_data_to_excel(ticker_a_trading_pricing, ticker_b_trading_pricing)

    # for da,p in trading_spread.items():

    #     print(da,p)

    # for price_date, price in spread.items():

    #     print(price_date, price)


connection = sqlite3.connect(r"C:\Users\sbuca\Desktop\2025-projects\stat-arb\prices.db")
cursor = connection.cursor()

dates = get_trading_dates("2025-08-29", cursor)
for curr_date in dates[-45:-15]:

    main(curr_date)
    print("\n\n")

# main("2025-08-13")