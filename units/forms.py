from django import forms
from .models import Unit

class UnitForm(forms.ModelForm):
    class Meta:
        model = Unit
        # Update these to match your models.py!
        fields = ['unit_name', 'house_type', 'rent']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control', 'placeholder': field.label})