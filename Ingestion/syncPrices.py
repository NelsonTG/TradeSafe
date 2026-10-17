import os
import psycopg2
import snowflake.connector
from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).resolve().parent.parent / "app" / ".env")


def get_snowflake():
    with open(os.environ["SNOWFLAKE_KEY_PATH"], "rb") as f:
        key = serialization.load_pem_private_key(f.read(), password=None)
    key_bytes = key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user="NELSONT",
        private_key=key_bytes,
        role="ACCOUNTADMIN",
        warehouse="SP500",
        database="TICKERS",
        schema="PUBLIC",
    )


def get_postgres():
    return psycopg2.connect(
        host="localhost",
        dbname="TradeSafe",
        user="tradesafe_app",
        password=os.environ["DB_PASSWORD"],
        port=5432,
    )


def main():
    sf = get_snowflake()
    try:
        cur = sf.cursor()
        cur.execute("select ticker, close_price from COMPANY_LATEST_PRICE")
        rows = cur.fetchall()
        cur.close()
    finally:
        sf.close()
    valid = [(t, p) for t, p in rows if t is not None and p is not None and p > 0]
    skipped = len(rows) - len(valid)
    pg = get_postgres()
    try:
        cur = pg.cursor()
        cur.executemany(
            """insert into latest_prices (ticker, price) values (%s, %s) on conflict (ticker) do update set price = excluded.price, updated_at = now()""",
            valid,)
        pg.commit()
        cur.close()
    except Exception:
        pg.rollback()
        raise
    finally:
        pg.close()

    print(f"read {len(rows)} rows, upserted {len(valid)}, skipped {skipped}")


if __name__ == "__main__":
    main()