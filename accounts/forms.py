from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class LandlordSignupForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'phone')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'LANDLORD'  # Explicitly set role
        user.is_first_login = False # Landlords set their own pass, so no need to change
        if commit:
            user.save()
        return user


from django import forms
from .models import User, Unit


class TenantCreationForm(forms.ModelForm):
    # This stays the same
    unit = forms.ModelChoiceField(queryset=Unit.objects.none())

    class Meta:
        model = User
        # ADD 'unit' TO THIS TUPLE
        fields = ('username', 'email', 'phone', 'first_name', 'last_name', 'unit')

    def __init__(self, *args, **kwargs):
        landlord = kwargs.pop('landlord', None)
        super().__init__(*args, **kwargs)

        if landlord:
            self.fields['unit'].queryset = Unit.objects.filter(landlord=landlord, status='Vacant')

        # Add Bootstrap styling
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'