"""URL patterns for the core VTU app."""
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    # Authentication
    path('register/', views.register_view, name='register'),
    path('login/', views.VTULoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html',
        email_template_name='registration/password_reset_email.html',
        subject_template_name='registration/password_reset_subject.txt',
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='registration/password_reset_complete.html'
    ), name='password_reset_complete'),

    # Dashboard
    path('', views.dashboard_view, name='dashboard'),

    # Wallet
    path('wallet/', views.wallet_view, name='wallet'),
    path('wallet/verify/', views.wallet_verify_view, name='wallet_verify'),
    path('wallet/webhook/', views.paystack_webhook, name='paystack_webhook'),  # ADD THIS LINE

    # Services
    path('services/data/', views.buy_data_view, name='buy_data'),
    path('services/airtime/', views.buy_airtime_view, name='buy_airtime'),
    path('services/cable/', views.cable_view, name='cable'),
    path('services/electricity/', views.electricity_view, name='electricity'),
    path('transactions/', views.transactions_view, name='transactions'),

    # AJAX endpoints
    path('ajax/data-plans/', views.ajax_get_data_plans, name='ajax_data_plans'),
    path('ajax/cable-bouquets/', views.ajax_get_cable_bouquets, name='ajax_cable_bouquets'),
    path('ajax/validate-decoder/', views.ajax_validate_decoder, name='ajax_validate_decoder'),
    path('ajax/validate-meter/', views.ajax_validate_meter, name='ajax_validate_meter'),
    
    path('webauthn/register/options/', views.webauthn_register_options, name='webauthn_register_options'),
    path('webauthn/register/verify/', views.webauthn_register_verify, name='webauthn_register_verify'),
    path('webauthn/login/options/', views.webauthn_login_options, name='webauthn_login_options'),
    path('webauthn/login/verify/', views.webauthn_login_verify, name='webauthn_login_verify'),
    
     # Paystack calls this URL directly (server-to-server), not the browser.
    # Configure this exact path as your webhook URL in the Paystack dashboard,
    # e.g. https://yourdomain.com/paystack/webhook/
    # path("paystack/webhook/", views.paystack_webhook, name="paystack_webhook")
]
