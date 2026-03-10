import pandas as pd
from stock_data import get_stock_data, load_watchlist
import time
from datetime import datetime
import sys
import argparse

# Load stocks from watchlist.json
# Usage: python export_report.py [group_name] [--force-refresh]
parser = argparse.ArgumentParser()
parser.add_argument('group_name', nargs='?', default=None)
parser.add_argument('--force-refresh', '-f', action='store_true')
args = parser.parse_args()
group_name = args.group_name
force_refresh = args.force_refresh
stock_list = load_watchlist(group_name)

# Create a mapping of stock_id -> list of groups for the CSV
import json
import os
watchlist_path = os.path.join(os.path.dirname(__file__), 'watchlist.json')
with open(watchlist_path, 'r') as f:
    full_watchlist = json.load(f)

stock_to_groups = {}
for g_name, s_ids in full_watchlist.items():
    for sid in s_ids:
        if sid not in stock_to_groups:
            stock_to_groups[sid] = []
        stock_to_groups[sid].append(g_name)

if not stock_list:
    print(f"No stocks found for group: {group_name if group_name else 'ALL'}")
    sys.exit(1)

results = []
desktop_path = os.path.expanduser("./")
base_filename = f"stock_report_{group_name + '_' if group_name else ''}{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
filename = os.path.join(desktop_path, base_filename)

print(f"Exporting data for {len(stock_list)} stocks to {filename}...")

for stock_id in stock_list:
    try:
        df = get_stock_data(stock_id, force_refresh=force_refresh)
        if df is not None and not df.empty:
            last_3 = df.tail(3)
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2]
            
            # Detect MACD Golden Cross
            macd_cross = "Yes" if (prev_row['macd'] <= prev_row['macd_signal'] and last_row['macd'] > last_row['macd_signal']) else "No"
            
            # Get individual values for last 3 days
            foreign_values = [int(row['foreign_net_buy']) for _, row in last_3.iterrows()]
            dates = [str(row['date']) for _, row in last_3.iterrows()]
            
            data = {
                'Stock_ID': stock_id,
                'Groups': ", ".join(stock_to_groups.get(stock_id, [])),
                'Price': last_row['close'],
                'K_Value': round(last_row['K'], 2),
                'D_Value': round(last_row['D'], 2),
                'MACD': round(last_row['macd'], 3),
                'MACD_Signal': round(last_row['macd_signal'], 3),
                'MACD_Golden_Cross': macd_cross
            }
            
            for i, (date, val) in enumerate(zip(dates, foreign_values)):
                data[f'Foreign_Net_Buy_{date}'] = val
            
            results.append(data)
        time.sleep(0.01)
    except Exception as e:
        print(f"Error {stock_id}: {e}")

if results:
    df_export = pd.DataFrame(results)
    df_export.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"DONE: Exported to {filename}")
else:
    print("FAILED: No data found.")
