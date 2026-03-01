import pandas as pd
from stock_data import get_stock_data
import time
from datetime import datetime

stock_list = [
    '6691', '4542', '6683', '2360', '1560', '7769', '5434', '6196', '6139', '2467', '6788', '6187', '2404', '8028', '6667', '3551', '3010', '3583', '3402', '6640', '3374',
    '6207', '2338', '5443', '3219', '4764', '1717', '1711', '4768', '4722', '1809', '1727', '4755', '1773', '1721'
]

results = []
filename = f"stock_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

print(f"Exporting data for {len(stock_list)} stocks to {filename}...")

for stock_id in stock_list:
    try:
        df = get_stock_data(stock_id)
        if df is not None and not df.empty:
            last_3 = df.tail(3)
            last_row = df.iloc[-1]
            
            # Get individual values for last 3 days
            foreign_values = [int(row['foreign_net_buy']) for _, row in last_3.iterrows()]
            dates = [str(row['date']) for _, row in last_3.iterrows()]
            
            data = {
                'Stock_ID': stock_id,
                'Price': last_row['close'],
                'K_Value': round(last_row['K'], 2),
                'D_Value': round(last_row['D'], 2),
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
