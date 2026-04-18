import requests
import base64
from datetime import datetime
from django.conf import settings
from requests.auth import HTTPBasicAuth


def get_access_token():
    """Generates the OAuth token from Safaricom using your Consumer Key and Secret."""
    api_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    try:
        response = requests.get(api_url,
                                auth=HTTPBasicAuth(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET))

        # Check if request was successful
        if response.status_code == 200:
            token = response.json().get('access_token')
            print(f"✅ Access token generated successfully: {token[:20]}...")  # For debugging
            return token
        else:
            print(f"❌ Failed to get token. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error getting access token: {e}")
        return None


def generate_stk_password():
    """Combines Shortcode, Passkey, and Timestamp for the Base64 STK Password."""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    raw_password = settings.MPESA_SHORTCODE + settings.MPESA_PASSKEY + timestamp
    stk_password = base64.b64encode(raw_password.encode()).decode('utf-8')
    print(f"✅ Password generated for timestamp: {timestamp}")  # For debugging
    return stk_password, timestamp


def initiate_stk_push(phone_number, amount, callback_url):
    """The main function that triggers the M-Pesa prompt on the phone."""
    # 1. Ensure phone is in format 2547XXXXXXXX
    original_phone = phone_number  # Keep original for logging
    if phone_number.startswith('0'):
        phone_number = '254' + phone_number[1:]
    elif phone_number.startswith('+'):
        phone_number = phone_number[1:]

    print(f"📱 Phone number formatted: {original_phone} → {phone_number}")

    # 2. Get credentials
    access_token = get_access_token()
    if not access_token:
        print("❌ Cannot proceed without access token")
        return {"ResponseCode": "1", "ResponseDescription": "Failed to get access token"}

    password, timestamp = generate_stk_password()

    # 3. Prepare the request
    headers = {"Authorization": f"Bearer {access_token}"}
    api_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"

    request_body = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone_number,
        "PartyB": settings.MPESA_SHORTCODE,
        "PhoneNumber": phone_number,
        "CallBackURL": callback_url,
        "AccountReference": "DBVIRM_RENT",
        "TransactionDesc": "Rent Payment"
    }

    print(f"📤 Sending STK push request to Safaricom...")
    print(f"📍 Amount: {amount}, Phone: {phone_number}")

    # 4. Send to Safaricom
    try:
        response = requests.post(api_url, json=request_body, headers=headers)
        result = response.json()

        # Check response
        if result.get("ResponseCode") == "0":
            print(f"✅ STK push initiated successfully!")
            print(f"📌 CheckoutRequestID: {result.get('CheckoutRequestID')}")
        else:
            print(f"❌ STK push failed: {result.get('ResponseDescription')}")

        return result
    except Exception as e:
        print(f"❌ Error sending STK push: {e}")
        return {"ResponseCode": "1", "ResponseDescription": str(e)}