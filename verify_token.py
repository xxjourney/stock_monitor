import os
from dotenv import load_dotenv
from FinMind.data import DataLoader

def verify():
    # 1. Check if .env is loaded
    load_dotenv()
    token = os.environ.get('FINMIND_API_TOKEN')
    
    if not token:
        print("❌ Error: FINMIND_API_TOKEN not found in .env file.")
        return

    print(f"✅ Token found in .env: {token[:5]}...{token[-5:]}")

    # 2. Try to login with FinMind
    try:
        api = DataLoader()
        api.login_by_token(api_token=token)
        print("✅ Successfully logged into FinMind with your token.")
        
        # 3. Test a small request
        print("📡 Testing API connection...")
        df = api.taiwan_stock_daily(
            stock_id='2330', 
            start_date='2024-01-01', 
            end_date='2024-01-02'
        )
        if not df.empty:
            print("✅ API connection test successful!")
        else:
            print("⚠️ API returned empty data, but login was successful.")
            
    except Exception as e:
        print(f"❌ Error during FinMind login/request: {str(e)}")

if __name__ == "__main__":
    verify()
