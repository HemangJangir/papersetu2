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
] 