from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from dbApp.utils import initiate_stk_push
from accounts.models import Lease,Payment,User
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime



@login_required
def process_payment(request):
    # 1. Get the tenant's lease to know how much they owe
    try:
        lease = Lease.objects.get(tenant=request.user)
        amount = lease.unit.rent
        phone = request.user.phone # Ensure your User model has a phone field
    except Lease.DoesNotExist:
        messages.error(request, "No active lease found. Please contact your landlord.")
        return redirect('tenant_dashboard')

    # 2. Define the Callback URL
    # For now, we use a placeholder. In production, this must be a public HTTPS URL.
    callback_url = "https://redemptory-nonpolitically-charmaine.ngrok-free.dev/mpesa/callback/"

    # 3. Trigger the STK Push
    response = initiate_stk_push(phone, amount, callback_url)

    # 4. Check if Safaricom accepted the request
    if response.get("ResponseCode") == "0":
        messages.success(request, "M-Pesa prompt sent! Enter your PIN on your phone.")
    else:
        error_msg = response.get("ResponseDescription", "Failed to initiate payment.")
        messages.error(request, f"Error: {error_msg}")

    return redirect('tenant_dashboard')


@csrf_exempt
def mpesa_callback(request):
    if request.method == 'POST':
        try:
            print("=" * 70)
            print("🔔 CALLBACK RECEIVED AT:", datetime.now())

            # Parse the request
            body = request.body.decode('utf-8')
            stk_data = json.loads(body)

            # Extract callback data
            stk_callback = stk_data['Body']['stkCallback']
            result_code = stk_callback['ResultCode']

            print(f"Result Code: {result_code}")

            if result_code == 0:
                # Extract metadata
                items = stk_callback['CallbackMetadata']['Item']

                # Initialize variables
                amount = None
                receipt = None
                phone = None

                # Loop through items safely
                for item in items:
                    if item['Name'] == 'Amount':
                        amount = item.get('Value')
                    elif item['Name'] == 'MpesaReceiptNumber':
                        receipt = item.get('Value')
                    elif item['Name'] == 'PhoneNumber':
                        phone = item.get('Value')

                print(f"✅ Extracted - Amount: {amount}, Receipt: {receipt}, Phone: {phone} (type: {type(phone)})")

                if not receipt:
                    print("❌ No receipt number found")
                    return JsonResponse({"ResultCode": 0, "ResultDesc": "Success"})

                # Convert phone to string and format
                if phone:
                    # Convert to string first
                    phone_str = str(phone)
                    print(f"Phone as string: {phone_str}")

                    if phone_str.startswith('254'):
                        lookup_phone = '0' + phone_str[3:]
                    else:
                        lookup_phone = phone_str
                else:
                    lookup_phone = None

                print(f"Looking up user with phone: {lookup_phone}")

                # Import models
                from accounts.models import User, Lease, Payment

                # Find user
                user = None
                if lookup_phone:
                    user = User.objects.filter(phone=lookup_phone).first()

                if not user:
                    print(f"❌ No user found with phone {lookup_phone}")
                    # List all users for debugging
                    print("Users in database:")
                    for u in User.objects.all():
                        print(f"  - {u.username}: '{u.phone}'")
                    return JsonResponse({"ResultCode": 0, "ResultDesc": "Success"})

                print(f"✅ Found user: {user.username}")

                # Find active lease
                lease = Lease.objects.filter(tenant=user, is_active=True).first()
                if not lease:
                    print(f"❌ No active lease for {user.username}")
                    return JsonResponse({"ResultCode": 0, "ResultDesc": "Success"})

                print(f"✅ Found lease for unit: {lease.unit.unit_name}")

                # Check if payment already exists
                existing = Payment.objects.filter(transaction_id=receipt).first()
                if existing:
                    print(f"⚠️ Payment {receipt} already exists")
                else:
                    # Create payment
                    payment = Payment.objects.create(
                        lease=lease,
                        amount=amount,
                        transaction_id=receipt,
                        is_confirmed=True
                    )
                    print(f"✅✅✅ PAYMENT SAVED! ID: {payment.id}")
                    print(f"   Receipt: {payment.transaction_id}")
                    print(f"   Amount: KES {payment.amount}")
                    print(f"   Date: {payment.date_paid}")

            print("=" * 70)
            return JsonResponse({"ResultCode": 0, "ResultDesc": "Success"})

        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({"ResultCode": 0, "ResultDesc": "Success"})

    return JsonResponse({"error": "Method not allowed"}, status=405)