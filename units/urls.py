from django.urls import path
from . import views

urlpatterns = [
    path('', views.unit_list, name='unit_list'),
    path('add/', views.add_unit, name='add_unit'),
    ]

