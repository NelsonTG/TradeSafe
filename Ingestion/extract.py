import requests, os, boto3, pandas, time, json
from io import StringIO
from massive import RESTClient

api = os.environ["massiveKey"]
client = RESTClient(api)
header = {
    "Authorization": f"Bearer {api}"
}
s3 = boto3.resource('s3')
# get S&P 500 list through wikipedia
#url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
# headers = {"User-Agent": "Mozilla/5.0"}
# response = requests.get(url, headers=headers)
# tables = pandas.read_html(StringIO(response.text))
# sp500 = tables[0]
# tickers = sp500["Symbol"].tolist()
# print(len(tickers))
# print(tickers[:10])
#Code to hardcode all S&P 500 companies to S3 ( 503 )
# for i in tickers:
#     for attempt in range(3):
#         try:
#             details = client.get_ticker_details(i)
#             data = details.__dict__
#             s3.Object("massivedata1",f"raw/ticker_details/{i}.json").put(Body=json.dumps(data,default = str))
#             print(f"Working {i}")
#             break
#         except Exception as e:
#             print(f"Failed on {i}:,c g {e}")
#             time.sleep(15)
#     time.sleep(12)

