from django.contrib.auth.models import AbstractUser
from django.db import models
from units.models import Unit

class User(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('LANDLORD', 'Landlord'),
        ('TENANT', 'Tenant'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='TENANT')
    phone = models.CharField(max_length=15, blank=True)
    is_first_login = models.BooleanField(default=True)

    # This ensures we can use email for login if we want later
    email = models.EmailField(unique=True)

    def __str__(self):
        return f"{self.username} ({self.role})"

# Now your other models look cleaner:

from django import forms
# 3. LEASE MODEL: Links a Tenant to a Unit
class Lease(models.Model):
    landlord = models.ForeignKey(User, on_delete=models.CASCADE, related_name='managed_leases')
    tenant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tenant_leases')
    unit = models.OneToOneField(Unit, on_delete=models.CASCADE)
    start_date = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.tenant.username} in {self.unit.unit_name}"

# 4. PAYMENT MODEL: For Daraja API (M-Pesa) and Receipts
class Payment(models.Model):
    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date_paid = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=100, unique=True) # M-Pesa Receipt Number
    is_confirmed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.transaction_id} - {self.amount}"


class MaintenanceRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
    ]

    tenant = models.ForeignKey(User, on_delete=models.CASCADE)
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __cl__str__(self):
        return f"{self.unit.unit_name} - {self.title}"

class TenantEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }