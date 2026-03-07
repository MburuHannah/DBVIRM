from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .utils import initiate_stk_push
from accounts.models import Lease,Payment
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt



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
@csrf_exempt  # Safaricom doesn't have your CSRF token, so we exempt this view
def mpesa_callback(request):
    if request.method == 'POST':
        # 1. Capture the data Safaricom sent
        stk_data = json.loads(request.body)
        result_code = stk_data['Body']['stkCallback']['ResultCode']

        # 2. ResultCode 0 means SUCCESS
        if result_code == 0:
            callback_metadata = stk_data['Body']['stkCallback']['CallbackMetadata']['Item']

            # Extract specific details (Amount, Receipt Number, etc.)
            amount = next(item['Value'] for item in callback_metadata if item['Name'] == 'Amount')
            mpesa_receipt = next(item['Value'] for item in callback_metadata if item['Name'] == 'MpesaReceiptNumber')
            phone = next(item['Value'] for item in callback_metadata if item['Name'] == 'PhoneNumber')

            # 3. Find the tenant and save the payment in your DB

            try:
                # 1. Find the active lease for this phone number
                # Note: Ensure your tenant's phone is saved as '254...' in the DB
                lease = Lease.objects.get(tenant__phone=str(phone), is_active=True)

                # 2. Create the payment record using the 'lease' field
                Payment.objects.create(
                    lease=lease,
                    amount=amount,
                    transaction_id=mpesa_receipt,
                    is_confirmed=True  # Since M-Pesa sent a success result
                )
                print(f"Payment recorded for {lease.tenant.username}")

            except Lease.DoesNotExist:
                print(f"Payment received for {phone} but no active lease found!")
        return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

    return JsonResponse({"Error": "Invalid request"}, status=400)