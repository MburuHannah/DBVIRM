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
from .models import User, Lease, Payment, MaintenanceRequest
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

    my_units = Unit.objects.filter(landlord=request.user)
    # Fetch all maintenance requests for the landlord's units
    maintenance_requests = MaintenanceRequest.objects.filter(unit__landlord=request.user).order_by('-created_at')

    # Count pending requests for a notification badge
    pending_count = maintenance_requests.filter(status='Pending').count()
    context = {
        'units': my_units,
        maintenance_requests: maintenance_requests,
        pending_count:pending_count,
        'total_units': my_units.count(),
        # Matches your dashboard filter
        'occupied_units': my_units.filter(status='Occupied').count(), 
    }
    return render(request, 'landlord_dashboard.html', context)

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


@login_required
def payment_history(request):
    if request.user.role != 'TENANT':
        return redirect('index')

    lease = Lease.objects.filter(tenant=request.user, is_active=True).first()

    payments = []
    total_paid = 0

    if lease:
        payments = Payment.objects.filter(lease=lease).order_by('-date_paid')
        # Calculate the sum of the 'amount' field for all payments
        total_paid = payments.aggregate(Sum('amount'))['amount__sum'] or 0

    return render(request, 'payment_history.html', {
        'payments': payments,
        'lease': lease,
        'total_paid': total_paid,
        'transaction_count': payments.count() if payments else 0
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
def update_maintenance_status(request, pk):
    if request.user.role == 'LANDLORD':
        req = get_object_or_404(MaintenanceRequest, pk=pk, unit__landlord=request.user)
        new_status = request.POST.get('status')
        req.status = new_status
        req.save()
        messages.success(request, f"Status for {req.title} updated to {new_status}.")
    return redirect('landlord_dashboard')