import akshare as ak
import pandas as pd
from datetime import datetime

def test_bid_ask(symbol):
    print(f"Testing bid_ask {symbol}...")
    try:
        # stock_bid_ask_em might return bid/ask levels
        df = ak.stock_bid_ask_em(symbol=symbol)
        print(df)
    except Exception as e:
        print(f"Error: {e}")

def test_hist(symbol):
    print(f"Testing hist {symbol}...")
    today = datetime.now().strftime("%Y%m%d")
    try:
        # daily hist
        df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date="20240101", adjust="qfq")
        print(df.tail(1))
    except Exception as e:
        print(f"Error: {e}")

print("--- Testing ETF 516650 ---")
test_bid_ask('516650')
# ETFs might use fund_etf_hist_em
try:
    print("ETF Hist:")
    df = ak.fund_etf_hist_em(symbol='516650', period='daily', start_date='20240101', adjust='qfq')
    print(df.tail(1))
except Exception as e:
    print(f"ETF Hist Error: {e}")

print("\n--- Testing Stock 600519 ---")
test_bid_ask('600519')
test_hist('600519')
