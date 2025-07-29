from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from functools import wraps

def verified_user_required(view_func):
    """
    Decorator that checks if the user is logged in and verified.
    If not verified, redirects to OTP verification page.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        if not request.user.is_verified:
            messages.warning(request, 'Please verify your email address to access this page.')
            return redirect('accounts:verify_otp')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def verified_login_required(view_func):
    """
    Combined decorator that requires both login and verification.
    """
    return verified_user_required(login_required(view_func)) 