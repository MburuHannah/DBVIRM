from django.urls import path
from dbApp import views

urlpatterns = [
    path('pay/', views.process_payment, name='process_payment'),
    path('mpesa/callback/', views.mpesa_callback, name='mpesa_callback'),

]