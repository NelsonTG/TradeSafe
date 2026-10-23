import json
import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import psycopg2
from confluent_kafka import Consumer
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / "app" / ".env")

UPSERT = """
insert into latest_prices (ticker, price, updated_at)
values (%s, %s, %s)
on conflict (ticker) do update
set price = excluded.price, updated_at = excluded.updated_at
where latest_prices.updated_at < excluded.updated_at
"""

consumer = Consumer({
    "bootstrap.servers": "localhost:9092",
    "group.id": "price-writer",
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False,
})
consumer.subscribe(["prices"])


def db():
    return psycopg2.connect(
        host="localhost", dbname="TradeSafe", user="tradesafe_app",
        password=os.environ["DB_PASSWORD"], port=5432,
    )


def parse(raw):
    try:
        event = json.loads(raw.decode("utf-8"))
        ticker = event["ticker"].upper()
        price = Decimal(event["price"])
        ts = datetime.fromisoformat(event["ts"])
    except Exception:
        return None
    if not price.is_finite() or price <= 0 or ts.tzinfo is None:
        return None
    return ticker, price, ts


def main():
    conn = db()
    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print("error:", msg.error())
                continue
            raw = msg.value()
            parsed = parse(raw) if raw is not None else None
            if parsed is None:
                print("skipping message at offset", msg.offset())
                consumer.commit(message=msg, asynchronous=False)
                continue
            ticker, price, ts = parsed
            try:
                with conn.cursor() as cur:
                    cur.execute(UPSERT, (ticker, price, ts))
                    applied = cur.rowcount
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            consumer.commit(message=msg, asynchronous=False)
            print(("applied" if applied else "stale, ignored"), ticker, price)
    except KeyboardInterrupt:
        pass
    finally:
        consumer.close()
        conn.close()


if __name__ == "__main__":
    main()