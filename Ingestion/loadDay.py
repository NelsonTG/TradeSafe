import sys
import snowflake.connector
from cryptography.hazmat.primitives import serialization

KEY_PATH = "/home/tingn/.dbt/snowflake_key.p8"

def private_key_bytes():
    with open(KEY_PATH, "rb") as f:
        key = serialization.load_pem_private_key(f.read(), password=None)
    return key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

def load(day):
    conn = snowflake.connector.connect(
        account="YP24488.us-east-2.aws",
        user="NELSONT",
        private_key=private_key_bytes(),
        role="ACCOUNTADMIN",
        warehouse="SP500",
        database="TICKERS",
        schema="PUBLIC",
    )
    try:
        cur = conn.cursor()
        cur.execute(f"""
            COPY INTO dailydata(rawData, fileName)
            FROM (SELECT $1, METADATA$FILENAME FROM @massivePrices/dt={day}/)
            FILE_FORMAT = (TYPE = 'JSON')
        """)
        print(cur.fetchall())
    finally:
        conn.close()

if __name__ == "__main__":
    load(sys.argv[1])