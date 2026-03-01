from stock_data import check_conditions
import time

stock_list = [
    "6691", "4542", "6683", "2360", "1560", "7769", "5434", "6196", "6139", "2467", "6788", "6187", "2404", "8028", "6667", "3551", "3010", "3583", "3402", "6640", "3374",
    "6207", "2338", "5443", "3219", "4764", "1717", "1711", "4768", "4722", "1809", "1727", "4755", "1773", "1721"
]

print(f"--- Checking {len(stock_list)} stocks from your photo ---")

matches = []
errors = []

for stock_id in stock_list:
    try:
        print(f"Checking {stock_id}...")
        is_met, msg = check_conditions(stock_id)
        if is_met:
            matches.append(msg)
        time.sleep(0.1) # Fast check
    except Exception as e:
        errors.append(f"Error checking {stock_id}: {str(e)}")

print("\n--- Summary ---")
if matches:
    print(f"Found {len(matches)} stocks matching your criteria:")
    for m in matches:
        print("\n" + m)
else:
    print("No stocks matched the criteria (K cross 20 + 3 days Foreign Net Buy) in the most recent trading days.")

if errors:
    print("\n--- Errors ---")
    for e in errors:
        print(e)
