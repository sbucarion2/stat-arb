import sqlite3

def build_db():

    connection = sqlite3.connect(r"C:\Users\sbuca\Desktop\2025-projects\stat-arb\prices.db")
    cursor = connection.cursor()

    # prices close is already adjusted for cacs on yfinance api
    try: 

        cursor.execute(
            """
            CREATE TABLE daily_prices(
                price_date text,
                ticker text,
                open real,
                high real,
                low real,
                close real
            );
            """
        )

    except Exception as e:

        print("*** BUILD ERROR: ", e, " ***")

    cursor.close()
    connection.close()

    return

build_db()