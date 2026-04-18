import secrets
import string
import json
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from django.http import JsonResponse

# Import models from both apps
from .models import User, Lease, Payment, MaintenanceRequest,TenantEditForm
from units.models import Unit
from .forms import LandlordSignupForm, TenantCreationForm

# 1. General Navigation
def index(request):
    return render(request, 'index.html')

@login_required
def login_redirect(request):
    """Directs users to the correct dashboard based on role."""
    user = request.user
    if user.role == 'LANDLORD':
        return redirect('landlord_dashboard')
    elif user.role == 'TENANT':
        if user.is_first_login:
            return redirect('password_change')
        return redirect('tenant_dashboard')
    return redirect('index')

# 2. Landlord Views
@login_required
def landlord_dashboard(request):
    if request.user.role != 'LANDLORD':
        return redirect('index')

    # Fetch units and the single lease attached to them
    units = Unit.objects.filter(landlord=request.user).select_related('lease__tenant')

    total_units = units.count()

    # A unit is occupied if it has a lease attached to it
    occupied_units = units.filter(lease__isnull=False).count()

    maintenance_requests = MaintenanceRequest.objects.filter(unit__landlord=request.user).order_by('-created_at')
    all_payments = Payment.objects.filter(lease__unit__landlord=request.user).order_by('-date_paid')

    return render(request, 'landlord_dashboard.html', {
        'units': units,
        'total_units': total_units,
        'occupied_units': occupied_units,
        'maintenance_requests': maintenance_requests,
        'all_payments': all_payments,
        'pending_count': maintenance_requests.filter(status='Pending').count(),
    })


@login_required
def tenant_detail(request, tenant_id):
    # Fetch the tenant user object
    tenant = get_object_or_404(User, id=tenant_id, role='TENANT')

    # Find the lease associated with this tenant
    # Since it's a OneToOneField on Unit, we look for it via the tenant
    lease = Lease.objects.filter(tenant=tenant, is_active=True).first()

    # Fetch their specific payments
    payments = Payment.objects.filter(lease=lease).order_add('-date_paid')

    return render(request, 'tenant_detail.html', {
        'tenant': tenant,
        'lease': lease,
        'payments': payments
    })
@login_required
def edit_tenant(request, tenant_id):
    tenant = get_object_or_404(User, id=tenant_id)
    if request.method == 'POST':
        form = TenantEditForm(request.POST, instance=tenant)
        if form.is_valid():
            form.save()
            messages.success(request, "Tenant details updated successfully!")
            return redirect('landlord_dashboard')
    else:
        form = TenantEditForm(instance=tenant)
    return render(request, 'edit_tenant.html', {'form': form, 'tenant': tenant})
@login_required
def end_lease(request, lease_id):
    if request.user.role == 'LANDLORD':
        lease = get_object_or_404(Lease, id=lease_id, unit__landlord=request.user)
        unit = lease.unit

        # 1. Mark lease as inactive
        lease.is_active = False
        lease.save()

        # 2. Make the unit vacant
        unit.is_occupied = False
        unit.save()

        messages.success(request, f"Lease ended for {unit.unit_name}. The unit is now Vacant.")
    return redirect('landlord_dashboard')

@login_required
def add_tenant(request):
    if request.user.role != 'LANDLORD':
        return redirect('index')

    if request.method == 'POST':
        form = TenantCreationForm(request.POST, landlord=request.user)
        if form.is_valid():
            # Generate temporary password
            alphabet = string.ascii_letters + string.digits
            temp_password = ''.join(secrets.choice(alphabet) for i in range(8))

            # Save the new Tenant User
            tenant_user = form.save(commit=False)
            tenant_user.set_password(temp_password)
            tenant_user.role = 'TENANT'
            tenant_user.is_first_login = True
            tenant_user.save()

            # Link Unit and Create Lease
            unit = form.cleaned_data['unit']
            Lease.objects.create(
                landlord=request.user,
                tenant=tenant_user,
                unit=unit,
                start_date=timezone.now(),
                is_active=True
            )

            # Mark unit as occupied in BOTH ways to ensure dashboard & logic work
            unit.status = 'Occupied'
            unit.is_occupied = True 
            unit.save()

            return render(request, 'tenant_success.html', {
                'temp_password': temp_password,
                'tenant_name': tenant_user.get_full_name()
            })
        else:
            # Check VS Code Terminal for these errors if button fails
            print(form.errors) 
            messages.error(request, "Please correct the errors below.")
    else:
        form = TenantCreationForm(landlord=request.user)

    return render(request, 'add_tenant.html', {'form': form})

# 3. Tenant Views
@login_required
def tenant_dashboard(request):
    if request.user.role != 'TENANT':
        return redirect('index')

    lease = Lease.objects.filter(tenant=request.user, is_active=True).first()

    # Fetch payments linked to this lease, newest first
    payments = []
    if lease:
        payments = Payment.objects.filter(lease=lease).order_by('-date_paid')

    context = {
        'lease': lease,
        'payments': payments,  # This is the key!
    }
    return render(request, 'tenant_dashboard.html', context)
# 4. Auth Views

from django.db.models import Sum  # Add this import at the top

from django.db.models import Sum


@login_required
def payment_history(request):
    if request.user.role != 'TENANT':
        messages.error(request, "Access denied")
        return redirect('dashboard')

    # Get tenant's payments
    payments = Payment.objects.filter(
        lease__tenant=request.user
    ).order_by('-date_paid')

    # Calculate total paid by this tenant
    total_paid = payments.aggregate(Sum('amount'))['amount__sum'] or 0

    print(f"Tenant {request.user.username} has {payments.count()} payments")

    return render(request, 'payment_history.html', {
        'payments': payments,
        'total_paid': total_paid
    })
def landlord_signup(request):
    if request.method == 'POST':
        form = LandlordSignupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created! Please login.")
            return redirect('login')
    else:
        form = LandlordSignupForm()
    return render(request, 'signup.html', {'form': form})

class TenantPasswordChangeView(PasswordChangeView):
    template_name = 'password_change.html'
    success_url = reverse_lazy('tenant_dashboard')

    def form_valid(self, form):
        user = self.request.user
        user.is_first_login = False
        user.save()
        messages.success(self.request, "Password updated! Welcome to your dashboard.")
        return super().form_valid(form)


from django.shortcuts import get_object_or_404


@login_required
def view_receipt(request, payment_id):
    # Ensure the tenant can only see THEIR own receipts
    payment = get_object_or_404(Payment, id=payment_id, lease__tenant=request.user)

    return render(request, 'receipt_detail.html', {'payment': payment})


@login_required
def maintenance_page(request):
    if request.user.role != 'TENANT':
        return redirect('index')

    lease = Lease.objects.filter(tenant=request.user, is_active=True).first()
    requests = MaintenanceRequest.objects.filter(tenant=request.user).order_by('-created_at')

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')

        if lease:
            MaintenanceRequest.objects.create(
                tenant=request.user,
                unit=lease.unit,
                title=title,
                description=description
            )
            messages.success(request, "Maintenance request submitted successfully!")
            return redirect('maintenance_page')

    return render(request, 'maintenance.html', {'requests': requests, 'lease': lease})


@login_required
def update_maintenance_status(request, req_id):
    if request.method == 'POST':
        new_status = request.POST.get('status')
        # Fetch the specific request from MySQL
        maintenance_item = MaintenanceRequest.objects.get(id=req_id)
        # Update the object and commit to DB
        maintenance_item.status = new_status
        maintenance_item.save()

    return redirect('maintenance_list')
from .forms import UnitEditForm, TenantEditForm

@login_required
def edit_unit(request, unit_id):
    unit = get_object_or_404(Unit, id=unit_id, landlord=request.user)
    if request.method == 'POST':
        form = UnitEditForm(request.POST, instance=unit)
        if form.is_valid():
            form.save()
            messages.success(request, f"Unit {unit.unit_name} updated!")
            return redirect('landlord_dashboard')
    else:
        form = UnitEditForm(instance=unit)
    return render(request, 'edit_unit.html', {'form': form, 'unit': unit})


@login_required
def edit_tenant(request, tenant_id):
    tenant = get_object_or_404(User, id=tenant_id, role='TENANT')

    # FIX: Use 'tenant_leases' instead of 'lease'
    # We use .first() because even if it's OneToOne, related_name acts like a set in some lookups
    active_lease = tenant.tenant_leases.filter(is_active=True).first()

    if request.method == 'POST':
        form = TenantEditForm(request.POST, instance=tenant)
        if form.is_valid():
            form.save()
            messages.success(request, "Tenant updated!")
            return redirect('manage_units')
    else:
        form = TenantEditForm(instance=tenant)

    return render(request, 'edit_tenant.html', {
        'form': form,
        'tenant': tenant,
        'lease': active_lease  # This ensures the "Assigned Unit" is not blank
    })


import africastalking
from django.contrib import messages

import africastalking
from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required


africastalking.initialize(settings.AT_USERNAME, settings.AT_API_KEY)
sms = africastalking.SMS

import africastalking
import requests
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

import requests
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages


def send_rent_reminder(request, tenant_id):
    tenant = get_object_or_404(User, id=tenant_id)

    # 1. Formatting the phone number
    raw_phone = str(tenant.phone).strip()
    clean_phone = "+254" + raw_phone[1:] if raw_phone.startswith('0') else raw_phone

    # 2. Hardcoding 'sandbox' to be 100% sure
    url = "https://api.sandbox.africastalking.com/version1/messaging"

    headers = {
        "ApiKey": settings.AT_API_KEY,
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    # Use 'sandbox' as the username
    data = {
        "username": "sandbox",
        "to": clean_phone,
        "message": f"Jambo {tenant.first_name}, rent for your unit is due. DBVIRM."
    }

    try:
        # 3. Sending the request (ignoring SSL errors we saw earlier)
        response = requests.post(url, data=data, headers=headers, verify=False)

        # This will print the error to your VS Code terminal so you can read it!
        print(f"DEBUG: Status {response.status_code}, Content: {response.text}")

        if response.status_code == 201:
            messages.success(request, "SMS Sent! Check the AT Simulator.")
        else:
            # If it fails, this will show you EXACTLY why (e.g., 'The supplied authentication is invalid')
            messages.error(request, f"AT Error: {response.text}")

    except Exception as e:
        messages.error(request, f"Connection Error: {str(e)}")

    return redirect('manage_units')

@login_required
def maintenance_list(request):
    # Only show requests for this landlord's units
    requests = MaintenanceRequest.objects.filter(unit__landlord=request.user).order_by('-created_at')
    return render(request, 'maintenance_list.html', {'maintenance_requests': requests})

@login_required
def manage_units(request):
    """The Detailed Property Inventory Page"""
    # select_related makes the page load faster by grabbing Tenant info in one go
    units = Unit.objects.filter(landlord=request.user).select_related('lease__tenant')
    return render(request, 'manage_units.html', {'units': units})


from django.db.models import Sum

from django.db.models import Sum


@login_required
def global_payments(request):
    payments = Payment.objects.all().order_by('-date_paid')
    total_amount = payments.aggregate(Sum('amount'))['amount__sum'] or 0

    return render(request, 'global_payments.html', {
        'payments': payments,
        'total_amount': total_amount
    })


@login_required
def tenant_detail(request, tenant_id):
    """Individual Tenant Profile Page"""
    tenant = get_object_or_404(User, id=tenant_id)
    # Get the single lease (OneToOneField)
    lease = getattr(tenant, 'lease', None)
    payments = Payment.objects.filter(lease=lease).order_by('-date_paid')

    return render(request, 'tenant_detail.html', {
        'tenant': tenant,
        'lease': lease,
        'payments': payments
    })


import africastalking
from django.conf import settings

# Make sure these are in your settings.py
africastalking.initialize(settings.AT_USERNAME, settings.AT_API_KEY)
sms = africastalking.SMS


@login_required
def update_maintenance_status(request, pk):
    if request.user.role != 'LANDLORD':
        return redirect('index')

    maintenance_req = get_object_or_404(MaintenanceRequest, id=pk)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        maintenance_req.status = new_status
        maintenance_req.save()

        # --- SMS NOTIFICATION LOGIC ---
        tenant = maintenance_req.tenant
        # Professional message format
        message = f"Hello {tenant.first_name}, the status of your repair request for '{maintenance_req.title}' has been updated to: {new_status}. Thank you, DBVIRM."

        try:
            # Send SMS via Africa's Talking
            sms.send(message, [str(tenant.phone)])
            messages.success(request, f"Status updated to {new_status}. Tenant notified via SMS.")
        except Exception as e:
            messages.warning(request, f"Status updated to {new_status}, but SMS notification failed: {str(e)}")

    return redirect('maintenance_list')

@login_required
def end_lease(request, lease_id):
    lease = get_object_or_404(Lease, id=lease_id)
    unit_name = lease.unit.unit_name
    lease.delete() # This makes unit.lease None, which shows "Vacant" in the table
    messages.warning(request, f"Lease terminated for {unit_name}. Unit is now vacant.")
    return redirect('manage_units')