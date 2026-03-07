from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.index, name='index'),  # Your Landing Page

    # Auth URLs
    path('signup/', views.landlord_signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # The Redirector
    path('dashboard/redirect/', views.login_redirect, name='login_redirect'),

    # Dashboards
    path('landlord/dashboard/', views.landlord_dashboard, name='landlord_dashboard'),
    path('tenant/dashboard/', views.tenant_dashboard, name='tenant_dashboard'),

    path('landlord/add-tenant', views.add_tenant, name='add_tenant'),

    path('password-change/', views.TenantPasswordChangeView.as_view(), name='password_change'),
    path('payment-history/', views.payment_history, name='payment_history'),
    path('receipt/<int:payment_id>/', views.view_receipt, name='view_receipt'),

    path('maintenance/', views.maintenance_page, name='maintenance_page'),

    path('maintenance/update/<int:pk>/', views.update_maintenance_status, name='update_maintenance_status'),

]
