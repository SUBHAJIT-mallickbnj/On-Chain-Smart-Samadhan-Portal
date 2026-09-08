import pandas as pd
import os
from datetime import datetime

def debug_complaints():
    """Debug script to check complaint data"""
    
    print("=== Blockchain Complaint System Debug ===\n")
    
    # Check if CSV file exists
    if os.path.exists("complaints.csv"):
        print("✅ complaints.csv found")
        try:
            df = pd.read_csv("complaints.csv", quoting=1, on_bad_lines="skip")
            print(f"📊 Total complaints in CSV: {len(df)}")
            
            if len(df) > 0:
                print("\n📋 Complaint Summary:")
                print(f"Columns: {list(df.columns)}")
                print(f"Unique wallets: {df['Wallet Address'].nunique()}")
                print(f"Date range: {df['Date'].min()} to {df['Date'].max()}")
                
                print("\n💰 Wallet addresses in file:")
                for wallet in df['Wallet Address'].unique():
                    count = len(df[df['Wallet Address'] == wallet])
                    print(f"  {wallet}: {count} complaints")
                
                print("\n📝 Recent complaints:")
                for _, complaint in df.tail(5).iterrows():
                    print(f"  {complaint['Reference No']} - {complaint['Wallet Address'][:10]}... - {complaint['Date']}")
            else:
                print("⚠️ CSV file is empty")
                
        except Exception as e:
            print(f"❌ Error reading CSV: {e}")
    else:
        print("❌ complaints.csv not found")
        # Create a sample entry
        sample_data = pd.DataFrame([{
            "Reference No": "TEST1234",
            "Wallet Address": "0x1234567890123456789012345678901234567890",
            "Name": "Test User",
            "Email": "test@example.com",
            "Phone": "+1234567890",
            "Address": "123 Test St",
            "City": "Test City",
            "State": "TS",
            "Zip": "12345",
            "Complaint": "This is a test complaint",
            "Department": "General",
            "Status": "Submitted",
            "Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Blockchain Status": "Success",
            "Transaction Hash": "0xtest123"
        }])
        sample_data.to_csv("complaints.csv", index=False)
        print("✅ Created sample complaints.csv")
    
    # Check other required files
    required_files = [
        "department_contacts.csv",
        "consumer_complaints.csv",
        ".env",
        "config.py",
        "blockchain_manager.py"
    ]
    
    print("\n📁 Required files check:")
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            print(f"❌ {file} missing")

if __name__ == "__main__":
    debug_complaints()