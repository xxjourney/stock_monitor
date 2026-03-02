import pandas as pd
from FinMind.data import DataLoader
import datetime
import json
import os

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

def get_stock_data(stock_id):
    api = DataLoader()
    
    # Get last 60 days to ensure enough data for KD smoothing
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=60)
    
    # 1. Fetch Price
    df_price = api.taiwan_stock_daily(
        stock_id=stock_id,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d")
    )
    if df_price.empty:
        return None
        
    # 2. Fetch Institutional Data (Foreign Investors)
    df_inst = api.taiwan_stock_institutional_investors(
        stock_id=stock_id,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d")
    )
    
    df_foreign = pd.DataFrame()
    if not df_inst.empty:
        df_foreign = df_inst[df_inst['name'] == 'Foreign_Investor'].copy()
        df_foreign['net_buy'] = df_foreign['buy'] - df_foreign['sell']
        df_foreign = df_foreign[['date', 'buy', 'sell', 'net_buy']]
        df_foreign.columns = ['date', 'foreign_buy', 'foreign_sell', 'foreign_net_buy']
        
    # 3. Calculate KD (standard 9 days)
    n = 9
    df_price['low_n'] = df_price['min'].rolling(window=n).min()
    df_price['high_n'] = df_price['max'].rolling(window=n).max()
    df_price['rsv'] = (df_price['close'] - df_price['low_n']) / (df_price['high_n'] - df_price['low_n']) * 100
    
    # Fill NaN RSV with 50 (standard practice)
    df_price['rsv'] = df_price['rsv'].fillna(50)
    
    k = [50.0]
    d = [50.0]
    
    for i in range(1, len(df_price)):
        current_k = (2/3) * k[-1] + (1/3) * df_price['rsv'].iloc[i]
        current_d = (2/3) * d[-1] + (1/3) * current_k
        k.append(current_k)
        d.append(current_d)
        
    df_price['K'] = k
    df_price['D'] = d
    
    # 4. Merge Price and Institutional Data
    if not df_foreign.empty:
        final_df = pd.merge(df_price, df_foreign, on='date', how='left')
    else:
        final_df = df_price
        final_df['foreign_net_buy'] = 0
        
    # Fill missing foreign data with 0 (days without institutional trading)
    final_df['foreign_net_buy'] = final_df['foreign_net_buy'].fillna(0)
    
    return final_df

def check_conditions(stock_id):
    df = get_stock_data(stock_id)
    if df is None or len(df) < 4:
        return False, f"Not enough data for {stock_id}"
        
    # Condition 1: K crosses 20 from low to high
    # Previous K <= 20, Current K > 20
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    k_cross_20 = prev_row['K'] <= 20 and last_row['K'] > 20
    
    # Condition 2: Foreign investors net buy for 3 consecutive days
    # Last 3 rows including today
    last_3_days = df.tail(3)
    foreign_buy_3_days = (last_3_days['foreign_net_buy'] > 0).all()
    
    if k_cross_20 and foreign_buy_3_days:
        msg = (
            f"🟢 Stock {stock_id} Alert!\n"
            f"Date: {last_row['date']}\n"
            f"K Value crossed 20: {prev_row['K']:.2f} -> {last_row['K']:.2f}\n"
            f"Foreign Net Buy (last 3 days):\n"
            f"1. {last_3_days.iloc[0]['date']}: {last_3_days.iloc[0]['foreign_net_buy']}\n"
            f"2. {last_3_days.iloc[1]['date']}: {last_3_days.iloc[1]['foreign_net_buy']}\n"
            f"3. {last_3_days.iloc[2]['date']}: {last_3_days.iloc[2]['foreign_net_buy']}"
        )
        return True, msg
        
    # For testing, we can print the current status if conditions are not met
    return False, f"Stock {stock_id} - Current K: {last_row['K']:.2f}, Last Foreign Net Buy: {last_row['foreign_net_buy']}"

if __name__ == "__main__":
    import sys
    stock_id = sys.argv[1] if len(sys.argv) > 1 else '2330'
    print(f"Checking conditions for {stock_id}...")
    is_met, msg = check_conditions(stock_id)
    print(f"Result: {is_met}")
    print(msg)
