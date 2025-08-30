import sqlite3

from tickers import PAIRS

# unnested_pairs = []
# for ticker_a, ticker_b in PAIRS:

#     unnested_pairs.append(ticker_a)
#     unnested_pairs.append(ticker_b)

# unnested_pairs = list(set(unnested_pairs))

# print(unnested_pairs)

def get_db_pairs(connection, cursor):

    cursor.execute(
        """
        SELECT *
        FROM ticker_pairs
        """
    )

    pairs = cursor.fetchall()

    return pairs


def load_pairs():

    connection = sqlite3.connect(r"C:\Users\sbuca\Desktop\2025-projects\stat-arb\prices.db")
    cursor = connection.cursor()

    db_pairs = get_db_pairs(connection, cursor)

    print(db_pairs)

    for ticker_a, ticker_b in PAIRS:

        if (ticker_a, ticker_b) in db_pairs:

            continue

        query = """INSERT INTO ticker_pairs (ticker_a, ticker_b) VALUES('{}', '{}')""".format(ticker_a, ticker_b)

        # print(query)

        cursor.execute(query)

        connection.commit()

    cursor.close()
    connection.close()

load_pairs()
