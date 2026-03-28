import pandas as pd
import pandas_ta as ta
from FinMind.data import DataLoader
import datetime
import json
import os
import time
from dotenv import load_dotenv

load_dotenv()

# Global DataLoader instance with token support
_api_instance = None

def get_api():
    global _api_instance
    if _api_instance is None:
        token = os.environ.get('FINMIND_API_TOKEN', '')
        _api_instance = DataLoader()
        if token:
            try:
                _api_instance.login_by_token(api_token=token)
                print(f"✅ FinMind API initialized with token: {token[:4]}...{token[-4:]}")
            except Exception as e:
                print(f"⚠️ Failed to login with token, falling back to guest mode: {e}")
        else:
            print("ℹ️ FinMind API initialized in guest mode (no token found in .env).")
    return _api_instance

def load_watchlist(group_name=None):
    path = os.path.join(os.path.dirname(__file__), 'watchlist.json')
    if not os.path.exists(path):
        return []
    
    with open(path, 'r') as f:
        data = json.load(f)
    
    if group_name:
        return data.get(group_name, [])
    
    # Return all unique stocks across all groups
    all_stocks = set()
    for stocks in data.values():
        all_stocks.update(stocks)
    return sorted(list(all_stocks))

def get_stock_data(stock_id, force_refresh=False):
    api = get_api()

    # 0. Check Cache
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    cache_dir = os.path.join(os.path.dirname(__file__), 'cache')
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    cache_file = os.path.join(cache_dir, f"{stock_id}_{today_str}.csv")
    inst_cache_file = os.path.join(cache_dir, f"{stock_id}_{today_str}_inst.csv")

    # Smart Cache Logic for merged data:
    # Use cache only if:
    # 1. Not forced to refresh
    # 2. File exists for TODAY
    # 3. On a trading day (weekday), if it's after 15:00, cache must also be created after 15:00
    #    On a non-trading day (weekend), always reuse cache — no new data will come in
    if not force_refresh and os.path.exists(cache_file):
        file_mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(cache_file))
        market_settle_time = now.replace(hour=15, minute=0, second=0, microsecond=0)
        is_trading_day = now.weekday() < 5  # Mon=0 ... Fri=4

        # Only bypass cache on weekdays after 15:00 if cache was created before 15:00
        if is_trading_day and now > market_settle_time and file_mod_time < market_settle_time:
            pass # Price refresh needed; inst cache may still be reused below
        else:
            return pd.read_csv(cache_file)

    # Get last 730 days (2 years) for absolute MACD stabilization
    # This provides ~480+ trading days, which is the industry standard for precision
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=730)

    try:
        # 1. Fetch Price
        df_price = api.taiwan_stock_daily(
            stock_id=stock_id,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d")
        )
        # Small delay between requests to stay under limit
        time.sleep(1.0)

        if df_price.empty:
            print(f"⚠️  FinMind returned no price data for {stock_id}")
            return None

        # 2. Load or Fetch Institutional Data (Foreign Investors)
        # Reuse inst cache only if its most recent date is today —
        # meaning today's data is already included. No hardcoded time needed.
        df_foreign = pd.DataFrame()
        if not force_refresh and os.path.exists(inst_cache_file):
            inst_mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(inst_cache_file))
            if inst_mod_time.date() == now.date():
                print(f"Using cached institutional data for {stock_id}")
                df_foreign = pd.read_csv(inst_cache_file)
        else:
            df_inst = api.taiwan_stock_institutional_investors(
                stock_id=stock_id,
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d")
            )
            time.sleep(1.0)

            if not df_inst.empty:
                df_foreign = df_inst[df_inst['name'] == 'Foreign_Investor'].copy()
                df_foreign['net_buy'] = df_foreign['buy'] - df_foreign['sell']
                df_foreign = df_foreign[['date', 'buy', 'sell', 'net_buy']]
                df_foreign.columns = ['date', 'foreign_buy', 'foreign_sell', 'foreign_net_buy']
                df_foreign.to_csv(inst_cache_file, index=False)

        # 3. Calculate KD (Taiwan Standard: RSV + 2/3, 1/3 smoothing)
        n = 9
        df_price['low_n'] = df_price['min'].rolling(window=n).min()
        df_price['high_n'] = df_price['max'].rolling(window=n).max()
        df_price['rsv'] = ((df_price['close'] - df_price['low_n']) / (df_price['high_n'] - df_price['low_n']) * 100).fillna(50)

        # In Taiwan, K/D smoothing is typically: Current = (1/3)*RSV + (2/3)*Prev_K
        # This is equivalent to an Exponential Moving Average with alpha=1/3 (com=2)
        df_price['K'] = df_price['rsv'].ewm(com=2, adjust=False).mean()
        df_price['D'] = df_price['K'].ewm(com=2, adjust=False).mean()

        # 4. Calculate MACD using pandas-ta
        # Fast=12, Slow=26, Signal=9
        macd = df_price.ta.macd(close='close', fast=12, slow=26, signal=9)
        if macd is not None and 'MACD_12_26_9' in macd.columns:
            df_price['macd'] = macd['MACD_12_26_9']
            df_price['macd_signal'] = macd['MACDs_12_26_9']
        else:
            # Fallback: compute MACD manually with min_periods=1 so sparse data still produces values
            ema12 = df_price['close'].ewm(span=12, min_periods=1, adjust=False).mean()
            ema26 = df_price['close'].ewm(span=26, min_periods=1, adjust=False).mean()
            df_price['macd'] = ema12 - ema26
            df_price['macd_signal'] = df_price['macd'].ewm(span=9, min_periods=1, adjust=False).mean()

        # 5. Merge Price and Institutional Data
        if not df_foreign.empty:
            final_df = pd.merge(df_price, df_foreign, on='date', how='left')
        else:
            final_df = df_price
            final_df['foreign_net_buy'] = 0

        # Fill missing foreign data with 0 (days without institutional trading)
        final_df['foreign_net_buy'] = final_df['foreign_net_buy'].fillna(0)

        # Save to Cache
        final_df.to_csv(cache_file, index=False)

        return final_df
    except Exception as e:
        print(f"Error fetching data for {stock_id}: {str(e)}")
        # If API limit hit, back off before the caller retries other stocks
        if "too many requests" in str(e).lower():
            time.sleep(30)
        # Fall back to stale cache if available; resave to update mtime so this
        # run counts as a valid post-15:00 fetch and won't trigger a retry loop.
        if os.path.exists(cache_file):
            print(f"Falling back to stale cache for {stock_id}")
            stale_df = pd.read_csv(cache_file)
            stale_df.to_csv(cache_file, index=False)  # Bump mtime to now
            return stale_df
        return None

def check_conditions(stock_id):
    df = get_stock_data(stock_id)
    if df is None or len(df) < 30: # Need more data for MACD stability
        return False, f"Not enough data for {stock_id}"
        
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    # Condition 1: K crosses 20 from low to high
    k_cross_20 = prev_row['K'] <= 20 and last_row['K'] > 20
    
    # Condition 2: Foreign investors net buy for 3 consecutive days
    last_3_days = df.tail(3)
    foreign_buy_3_days = (last_3_days['foreign_net_buy'] > 0).all()

    # Condition 3: MACD Golden Cross
    macd_golden_cross = prev_row['macd'] <= prev_row['macd_signal'] and last_row['macd'] > last_row['macd_signal']
    
    alerts = []
    if k_cross_20 and foreign_buy_3_days:
        alerts.append("🔥 Advanced Filter: K > 20 Cross + 3 Days Foreign Net Buy")
    
    if macd_golden_cross:
        alerts.append("✨ MACD Golden Cross: MACD line crossed above Signal line")

    if alerts:
        msg = (
            f"🔔 Stock {stock_id} Signal!\n"
            f"Date: {last_row['date']}\n"
            f"Price: {last_row['close']}\n"
            f"K Value: {last_row['K']:.2f}\n"
            f"MACD: {last_row['macd']:.2f}, Signal: {last_row['macd_signal']:.2f}\n\n"
            "Signals:\n" + "\n".join(alerts)
        )
        return True, msg
        
    return False, f"Stock {stock_id} - K: {last_row['K']:.2f}, MACD: {last_row['macd']:.2f}, Signal: {last_row['macd_signal']:.2f}"

if __name__ == "__main__":
    import sys
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('stock_id', nargs='?', default='2330')
    parser.add_argument('--force-refresh', '-f', action='store_true')
    args = parser.parse_args()
    if args.force_refresh:
        print(f"Force refreshing data for {args.stock_id}...")
        get_stock_data(args.stock_id, force_refresh=True)
    print(f"Checking conditions for {args.stock_id}...")
    is_met, msg = check_conditions(args.stock_id)
    print(f"Result: {is_met}")
    print(msg)
