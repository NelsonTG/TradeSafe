import os, json, boto3
import sys
from massive import RESTClient

client = RESTClient(os.environ["massiveKey"])
s3 = boto3.resource("s3")
def ingest(day):
    bars = list(client.get_grouped_daily_aggs(day))
    if not bars:
        return
    body = "\n".join(json.dumps(b.__dict__) for b in bars)
    key = f"raw/daily_prices/dt={day}/bars.json"
    s3.Object("massivedata1", key).put(Body=body)
    print(f"{day}: wrote {len(bars)} bars to {key}")
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python dailyIngest.py YYYY-MM-DD")
        sys.exit(1)
    ingest(sys.argv[1])