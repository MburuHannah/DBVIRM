from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Unit
from django.contrib import messages


@login_required
def unit_list(request):
    units = Unit.objects.all()
    return render(request, 'unit_list.html', {'units': units})




from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import UnitForm


@login_required
def add_unit(request):
    if request.user.role != 'LANDLORD':
        return redirect('index')

    if request.method == 'POST':
        form = UnitForm(request.POST)
        if form.is_valid():
            unit = form.save(commit=False)
            unit.landlord = request.user  # Link the unit to the logged-in Landlord
            unit.save()
            messages.success(request, f"Unit {unit.unit_name} has been added successfully!")
            return redirect('landlord_dashboard')
    else:
        form = UnitForm()

    return render(request, 'add_unit.html', {'form': form})



