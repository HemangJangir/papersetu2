from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib import messages
from django.utils import timezone
from django.core.mail import send_mail
from .forms import UserRegistrationForm, PasswordResetEmailForm, PasswordResetOTPForm, SetNewPasswordForm
from .models import User
import random
from django.contrib.auth.views import LoginView, PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.hashers import make_password
import string
from django.views import View

class CombinedAuthView(LoginView):
    template_name = 'accounts/login.html'

    def post(self, request, *args, **kwargs):
        if 'signup' in request.POST:
            # Handle sign up
            form = UserRegistrationForm(request.POST)
            if form.is_valid():
                user = form.save(commit=False)
                user.is_active = False
                otp = str(random.randint(100000, 999999))
                user.otp = otp
                user.otp_created_at = timezone.now()
                user.save()
                send_mail(
                    'Your OTP for PaperSetu Registration',
                    f'Your OTP is: {otp}',
                    'noreply@papersetu.com',
                    [user.email],
                    fail_silently=False,
                )
                request.session['pending_user_id'] = user.id
                return redirect('accounts:verify_otp')
            else:
                # Render the page with registration errors
                return render(request, self.template_name, {
                    'form': self.get_form(self.get_form_class()),
                    'signup_form': form,
                    'show_signup': True
                })
        else:
            # Handle login (default LoginView behavior)
            return super().post(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {
            'form': self.get_form(self.get_form_class()),
            'signup_form': UserRegistrationForm(),
            'show_signup': False
        })

def verify_otp(request):
    user_id = request.session.get('pending_user_id')
    if not user_id:
        return redirect('accounts:login')
    user = User.objects.get(id=user_id)
    if request.method == 'POST':
        otp_input = request.POST.get('otp')
        if otp_input == user.otp:
            user.is_active = True
            user.is_verified = True
            user.otp = ''
            user.save()
            messages.success(request, 'Account verified! You can now log in.')
            return redirect('accounts:login')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')
    return render(request, 'accounts/verify_otp.html')

def custom_logout(request):
    logout(request)
    return redirect('/')

def password_reset_request(request):
    if request.method == 'POST':
        form = PasswordResetEmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                otp = ''.join(random.choices(string.digits, k=6))
                user.otp = otp
                user.otp_created_at = timezone.now()
                user.save()
                send_mail(
                    'Your OTP for Password Reset',
                    f'Your OTP is: {otp}',
                    'noreply@conference.com',
                    [user.email],
                    fail_silently=False,
                )
                request.session['reset_user_id'] = user.id
                return redirect('accounts:password_reset_otp')
            except ObjectDoesNotExist:
                messages.error(request, 'No user found with that email.')
    else:
        form = PasswordResetEmailForm()
    return render(request, 'accounts/password_reset_email.html', {'form': form})

def password_reset_otp(request):
    user_id = request.session.get('reset_user_id')
    if not user_id:
        return redirect('accounts:password_reset_request')
    user = User.objects.get(id=user_id)
    if request.method == 'POST':
        form = PasswordResetOTPForm(request.POST)
        if form.is_valid():
            otp_input = form.cleaned_data['otp']
            # OTP valid for 10 minutes
            if user.otp == otp_input and user.otp_created_at and (timezone.now() - user.otp_created_at).total_seconds() < 600:
                request.session['otp_verified'] = True
                return redirect('accounts:password_reset_new')
            else:
                messages.error(request, 'Invalid or expired OTP.')
    else:
        form = PasswordResetOTPForm()
    return render(request, 'accounts/password_reset_otp.html', {'form': form})

def password_reset_new(request):
    user_id = request.session.get('reset_user_id')
    otp_verified = request.session.get('otp_verified')
    if not user_id or not otp_verified:
        return redirect('accounts:password_reset_request')
    user = User.objects.get(id=user_id)
    if request.method == 'POST':
        form = SetNewPasswordForm(user, request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data['new_password1'])
            user.otp = ''
            user.otp_created_at = None
            user.save()
            # Clear session
            request.session.pop('reset_user_id', None)
            request.session.pop('otp_verified', None)
            messages.success(request, 'Password reset successful. You can now log in.')
            return redirect('accounts:login')
    else:
        form = SetNewPasswordForm(user)
    return render(request, 'accounts/password_reset_new.html', {'form': form}) 