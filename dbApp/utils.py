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
        return response.json().get('access_token')
    except Exception:
        return None


def generate_stk_password():
    """Combines Shortcode, Passkey, and Timestamp for the Base64 STK Password."""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    raw_password = settings.MPESA_SHORTCODE + settings.MPESA_PASSKEY + timestamp
    stk_password = base64.b64encode(raw_password.encode()).decode('utf-8')
    return stk_password, timestamp


def initiate_stk_push(phone_number, amount, callback_url):
    """The main function that triggers the M-Pesa prompt on the phone."""
    # 1. Ensure phone is in format 2547XXXXXXXX
    if phone_number.startswith('0'):
        phone_number = '254' + phone_number[1:]
    elif phone_number.startswith('+'):
        phone_number = phone_number[1:]

    # 2. Get credentials
    access_token = get_access_token()
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

    # 4. Send to Safaricom
    response = requests.post(api_url, json=request_body, headers=headers)
    return response.json()