#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QBot - Google Sheets Authentication Helper
Xác thực và tạo token.json cho Google Sheets API
"""

import os
import sys
from pathlib import Path

def main():
    """Main authentication function"""
    print("")
    print("=" * 70)
    print("🔐 QBot - Google Sheets Authentication")
    print("=" * 70)
    print("")
    
    # Check if credentials.json exists
    if not os.path.exists('credentials.json'):
        print("❌ ERROR: credentials.json not found!")
        print("")
        print("💡 Please follow these steps:")
        print("   1. Go to https://console.cloud.google.com/")
        print("   2. Create a new project or select existing one")
        print("   3. Go to 'APIs & Services' → 'Credentials'")
        print("   4. Click 'CREATE CREDENTIALS' → 'OAuth client ID'")
        print("   5. Application type: 'Desktop app'")
        print("   6. Download JSON file and rename to 'credentials.json'")
        print("   7. Copy file to:", os.getcwd())
        print("")
        return 1
    
    print("✅ Found credentials.json")
    print("")
    
    # Import required libraries
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        import gspread
    except ImportError as e:
        print(f"❌ ERROR: Missing required library: {e}")
        print("")
        print("💡 Please run: 1_setup_install.bat")
        print("")
        return 1
    
    # Define scopes
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    creds = None
    
    # Check for existing token (sử dụng token.json để đồng nhất với gg_sheet_factory.py)
    if os.path.exists('token.json'):
        print("📂 Found existing token.json, checking validity...")
        try:
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            print("✅ Token loaded successfully")
        except Exception as e:
            print(f"⚠️  Warning: Could not load token: {e}")
            creds = None
    
    # Authenticate if needed
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("")
            print("🔄 Token expired, refreshing...")
            try:
                creds.refresh(Request())
                print("✅ Token refreshed successfully")
            except Exception as e:
                print(f"⚠️  Refresh failed: {e}")
                print("🌐 Starting new authentication flow...")
                creds = None
        
        if not creds:
            print("")
            print("🌐 Opening browser for authentication...")
            print("")
            print("📝 Next steps:")
            print("   1. Browser will open automatically")
            print("   2. Login with your Google account")
            print("   3. Click 'Allow' to grant permissions")
            print("   4. Close browser and return here")
            print("")
            
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
                print("")
                print("✅ Authentication successful!")
            except Exception as e:
                print("")
                print(f"❌ Authentication failed: {e}")
                print("")
                print("💡 Possible causes:")
                print("   1. credentials.json format is incorrect")
                print("   2. Google Sheets API not enabled")
                print("   3. OAuth consent screen not configured")
                print("")
                return 1
        
        # Save credentials (sử dụng token.json để đồng nhất với gg_sheet_factory.py)
        print("")
        print("💾 Saving credentials to token.json...")
        try:
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
            print("✅ Credentials saved successfully")
        except Exception as e:
            print(f"⚠️  Warning: Could not save token: {e}")
    
    # Test connection
    print("")
    print("🔍 Testing connection to Google Sheets API...")
    try:
        gc = gspread.authorize(creds)
        print("✅ Connection successful!")
        
        # List spreadsheets
        print("")
        print("=" * 70)
        print("📊 Your Spreadsheets (first 10):")
        print("=" * 70)
        print("")
        
        spreadsheets = gc.openall()
        if not spreadsheets:
            print("   ℹ️  No spreadsheets found")
        else:
            for i, sheet in enumerate(spreadsheets[:10], 1):
                print(f"   {i}. {sheet.title}")
                print(f"      ID: {sheet.id}")
                print(f"      URL: https://docs.google.com/spreadsheets/d/{sheet.id}")
                print("")
        
        print("=" * 70)
        print("")
        print("✅ AUTHENTICATION COMPLETED SUCCESSFULLY!")
        print("")
        print("📝 Next steps:")
        print("   1. Copy Spreadsheet ID above")
        print("   2. Open config.ini")
        print("   3. Set spreadsheet_id = YOUR_SPREADSHEET_ID")
        print("   4. Run: 2_check_environment.bat")
        print("")
        return 0
        
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        print("")
        print("💡 Please check:")
        print("   1. Google Sheets API is enabled")
        print("   2. credentials.json is correct")
        print("   3. OAuth consent screen is configured")
        print("")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("")
        print("")
        print("⚠️  Authentication cancelled by user")
        print("")
        sys.exit(1)
    except Exception as e:
        print("")
        print(f"❌ Unexpected error: {e}")
        print("")
        import traceback
        traceback.print_exc()
        sys.exit(1)

