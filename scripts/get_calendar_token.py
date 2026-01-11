"""
Google Calendar OAuth Token Exchange Script
============================================

This script performs the one-time OAuth flow to get a refresh token
for Google Calendar access. Run this locally, then store the refresh
token in Google Secret Manager.

Prerequisites:
1. Download OAuth credentials JSON from GCP Console
2. pip install google-auth-oauthlib google-api-python-client

Usage:
    python get_calendar_token.py

After running:
    - Copy the refresh token
    - Store in Secret Manager: google-calendar-refresh-token
"""

import os
import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Scopes needed for calendar read/write
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',  # Read events
    'https://www.googleapis.com/auth/calendar.events',     # Create/modify events
]

def get_credentials_path():
    """Find the OAuth credentials file."""
    possible_paths = [
        Path.home() / "Downloads" / "oauth_credentials.json",
        Path.home() / "Downloads" / "client_secret.json",
        Path.home() / "Downloads" / "credentials.json",
        Path("oauth_credentials.json"),
        Path("client_secret.json"),
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
    
    # List what's in Downloads to help user
    downloads = Path.home() / "Downloads"
    json_files = list(downloads.glob("*.json"))
    
    print("\n❌ Could not find OAuth credentials file.")
    print("\nLooking for: oauth_credentials.json or client_secret*.json")
    print(f"\nJSON files in {downloads}:")
    for f in json_files[:10]:
        print(f"  - {f.name}")
    
    print("\n📋 Instructions:")
    print("1. Go to: https://console.cloud.google.com/apis/credentials")
    print("2. Click your OAuth 2.0 Client ID")
    print("3. Click 'Download JSON'")
    print("4. Save as 'oauth_credentials.json' in your Downloads folder")
    print("5. Run this script again")
    
    return None


def main():
    print("=" * 60)
    print("Google Calendar OAuth Token Exchange")
    print("=" * 60)
    
    # Find credentials file
    creds_path = get_credentials_path()
    if not creds_path:
        return
    
    print(f"\n✅ Found credentials: {creds_path}")
    
    # Run OAuth flow
    print("\n🌐 Opening browser for Google sign-in...")
    print("   (If browser doesn't open, check the terminal for a URL)")
    
    try:
        flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
        credentials = flow.run_local_server(port=8090, prompt='consent')
    except Exception as e:
        print(f"\n❌ OAuth flow failed: {e}")
        print("\nTroubleshooting:")
        print("- Make sure you're signed into Google in your browser")
        print("- Check that port 8090 is not in use")
        print("- Try running as administrator")
        return
    
    # Success! Show the tokens
    print("\n" + "=" * 60)
    print("✅ SUCCESS! Here are your tokens:")
    print("=" * 60)
    
    print(f"\n📌 REFRESH TOKEN (save this to Secret Manager):\n")
    print("-" * 60)
    print(credentials.refresh_token)
    print("-" * 60)
    
    print(f"\n📌 Access Token (temporary, expires in ~1 hour):")
    print(credentials.token[:50] + "..." if credentials.token else "None")
    
    print(f"\n📌 Client ID:")
    print(credentials.client_id[:50] + "..." if credentials.client_id else "None")
    
    # Save to file for reference
    token_data = {
        "refresh_token": credentials.refresh_token,
        "token": credentials.token,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "token_uri": credentials.token_uri,
    }
    
    token_file = Path("calendar_tokens.json")
    with open(token_file, "w") as f:
        json.dump(token_data, f, indent=2)
    
    print(f"\n💾 Tokens also saved to: {token_file.absolute()}")
    
    # Test the token
    print("\n🧪 Testing calendar access...")
    try:
        service = build('calendar', 'v3', credentials=credentials)
        calendars = service.calendarList().list().execute()
        print(f"✅ Success! Found {len(calendars.get('items', []))} calendars:")
        for cal in calendars.get('items', [])[:5]:
            print(f"   - {cal['summary']}")
    except Exception as e:
        print(f"❌ Calendar test failed: {e}")
    
    # Instructions for Secret Manager
    print("\n" + "=" * 60)
    print("📋 NEXT STEPS:")
    print("=" * 60)
    print("""
1. Copy the REFRESH TOKEN above

2. Store in Secret Manager:
   
   PowerShell:
   $refreshToken = "PASTE_REFRESH_TOKEN_HERE"
   $refreshToken | gcloud secrets create google-calendar-refresh-token --data-file=- --project=metapm
   
   Or if secret exists:
   $refreshToken | gcloud secrets versions add google-calendar-refresh-token --data-file=- --project=metapm

3. Store Client ID and Secret (from the JSON you downloaded):
   
   # Find these in oauth_credentials.json under "installed" or "web"
   gcloud secrets create google-oauth-client-id --data-file=- --project=metapm
   gcloud secrets create google-oauth-client-secret --data-file=- --project=metapm

4. Grant Cloud Run access to these secrets:
   
   $sa = "metapm-cloud-run@metapm.iam.gserviceaccount.com"
   gcloud secrets add-iam-policy-binding google-calendar-refresh-token --member="serviceAccount:$sa" --role="roles/secretmanager.secretAccessor" --project=metapm
   gcloud secrets add-iam-policy-binding google-oauth-client-id --member="serviceAccount:$sa" --role="roles/secretmanager.secretAccessor" --project=metapm
   gcloud secrets add-iam-policy-binding google-oauth-client-secret --member="serviceAccount:$sa" --role="roles/secretmanager.secretAccessor" --project=metapm

5. Update Cloud Run deployment to include new secrets:
   
   --set-secrets "...,GOOGLE_CALENDAR_REFRESH_TOKEN=google-calendar-refresh-token:latest,GOOGLE_OAUTH_CLIENT_ID=google-oauth-client-id:latest,GOOGLE_OAUTH_CLIENT_SECRET=google-oauth-client-secret:latest"
""")


if __name__ == "__main__":
    main()
