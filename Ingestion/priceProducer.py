import json
import os
import random
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import psycopg2
from confluent_kafka import Producer
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / "app" / ".env")

TOPIC = "prices"
DELAY = float(os.environ.get("PRICE_DELAY", "12"))

producer = Producer({"bootstrap.servers": "localhost:9092"})
last_simulated = {}
real_ok = True


def db():
    return psycopg2.connect(
        host="localhost", dbname="TradeSafe", user="tradesafe_app",
        password=os.environ["DB_PASSWORD"], port=5432,
    )


def held_tickers(conn):
    with conn.cursor() as cur:
        cur.execute(
            "select distinct ticker from holdings where shares > 0 order by ticker"
        )
        rows = cur.fetchall()
    conn.commit()
    return [r[0] for r in rows]


def real_price(client, ticker):
    trade = client.get_last_trade(ticker)
    return Decimal(str(trade.price))


def simulated_price(conn, ticker):
    base = last_simulated.get(ticker)
    if base is None:
        with conn.cursor() as cur:
            cur.execute("select price from latest_prices where ticker = %s", (ticker,))
            row = cur.fetchone()
        conn.commit()
        if row is None:
            return None
        base = row[0]
    move = Decimal(str(round(random.uniform(-0.003, 0.003), 6)))
    new = (base * (1 + move)).quantize(Decimal("0.01"))
    last_simulated[ticker] = new
    return new


def fetch_price(client, conn, ticker):
    global real_ok
    if client is not None and real_ok:
        try:
            return real_price(client, ticker), "massive"
        except Exception as e:
            real_ok = False
            print("real price unavailable, switching to simulated:", e)
    return simulated_price(conn, ticker), "simulated"


def on_delivery(err, msg):
    if err is not None:
        print("delivery failed:", err)


def main():
    client = None
    key = os.environ.get("massiveKey")
    if key:
        from massive import RESTClient
        client = RESTClient(key)

    conn = db()
    try:
        while True:
            tickers = held_tickers(conn)
            if not tickers:
                print("no held tickers yet")
                time.sleep(DELAY)
                continue
            for ticker in tickers:
                price, source = fetch_price(client, conn, ticker)
                if price is not None and price > 0:
                    event = {
                        "ticker": ticker,
                        "price": str(price),
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "source": source,
                    }
                    producer.produce(
                        TOPIC, key=ticker, value=json.dumps(event), callback=on_delivery
                    )
                    producer.flush(10)
                    print("published", event)
                time.sleep(DELAY)
    except KeyboardInterrupt:
        pass
    finally:
        producer.flush(10)
        conn.close()


if __name__ == "__main__":
    main()