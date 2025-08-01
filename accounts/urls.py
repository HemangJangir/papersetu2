from django.urls import path
from . import views
from .views import CombinedAuthView, custom_logout
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView

app_name = 'accounts'

urlpatterns = [
    # path('register/', views.register, name='register'),  # Remove or comment out
    path('login/', CombinedAuthView.as_view(), name='login'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('logout/', custom_logout, name='logout'),
    path('password-reset/', views.password_reset_request, name='password_reset_request'),
    path('password-reset/otp/', views.password_reset_otp, name='password_reset_otp'),
    path('password-reset/new/', views.password_reset_new, name='password_reset_new'),
    # Add the missing password reset confirm URL pattern
    path('password-reset-confirm/<uidb64>/<token>/', PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        success_url='/accounts/password-reset-complete/'
    ), name='password_reset_confirm'),
    path('password-reset-complete/', PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'
    ), name='password_reset_complete'),
] 