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
                user.set_password(form.cleaned_data['password1'])
                user.save()
                
                # Link PC invites to the newly created user
                self.link_pc_invites(user, form)
                
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
            # SAFETY NET: If user exists and password is correct but is_active/is_verified is False, fix and log in
            username = request.POST.get('username')
            password = request.POST.get('password')
            user = None
            if username and password:
                try:
                    user_obj = User.objects.get(username=username)
                except User.DoesNotExist:
                    try:
                        user_obj = User.objects.get(email=username)
                    except User.DoesNotExist:
                        user_obj = None
                if user_obj and user_obj.check_password(password):
                    if not user_obj.is_active or not user_obj.is_verified:
                        user_obj.is_active = True
                        user_obj.is_verified = True
                        user_obj.save()
                        auth_login(request, user_obj)
                        return redirect('dashboard:dashboard')
            return super().post(request, *args, **kwargs)

    def link_pc_invites(self, user, form):
        """Link PC invites to the newly created user"""
        try:
            from conference.models import PCInvite, UserConferenceRole
            from django.utils import timezone
            
            # Get PC invites from form if available
            pc_invites = getattr(form, 'accepted_invites', None)
            
            if not pc_invites:
                # Fallback: find PC invites for this email
                pc_invites = PCInvite.objects.filter(email=user.email)
            
            for invite in pc_invites:
                if invite.status == 'pending':
                    # Scenario 2: User registers first, then accepts invite
                    # Auto-accept the pending invite
                    invite.status = 'accepted'
                    invite.accepted_at = timezone.now()
                    invite.save()
                    
                    # Create UserConferenceRole
                    UserConferenceRole.objects.get_or_create(
                        user=user,
                        conference=invite.conference,
                        role='pc_member',
                        track=invite.track
                    )
                    
                    # Send notification to chair
                    try:
                        from conference.models import Notification
                        Notification.objects.create(
                            recipient=invite.invited_by,
                            notification_type='reviewer_response',
                            title=f'PC Member Accepted Invitation',
                            message=f'{user.get_full_name()} ({user.email}) has accepted the PC member invitation for {invite.conference.name}.',
                            related_conference=invite.conference
                        )
                    except:
                        pass  # Don't fail if notification creation fails
                
                elif invite.status == 'accepted':
                    # Scenario 1: User accepted invite first, then registers
                    # Just create the UserConferenceRole
                    UserConferenceRole.objects.get_or_create(
                        user=user,
                        conference=invite.conference,
                        role='pc_member',
                        track=invite.track
                    )
                    
        except ImportError:
            pass  # Don't fail if conference app is not available

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
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'Invalid verification session. Please try signing up again.')
        return redirect('accounts:login')
    
    if request.method == 'POST':
        # Handle resend OTP
        if 'resend_otp' in request.POST:
            # Generate new OTP
            otp = str(random.randint(100000, 999999))
            user.otp = otp
            user.otp_created_at = timezone.now()
            user.save()
            
            # Send new OTP email
            try:
                send_mail(
                    'Your OTP for PaperSetu Registration',
                    f'Your new OTP is: {otp}',
                    'noreply@papersetu.com',
                    [user.email],
                    fail_silently=False,
                )
                messages.success(request, 'New OTP has been sent to your email.')
            except Exception as e:
                messages.error(request, 'Failed to send OTP. Please try again later.')
                user.otp = ''
                user.otp_created_at = None
                user.save()
            
            return render(request, 'accounts/verify_otp.html')
        
        # Handle OTP verification
        otp_input = request.POST.get('otp', '').strip()
        
        # Check if OTP was provided
        if not otp_input:
            messages.error(request, 'Please enter the OTP sent to your email.')
            return render(request, 'accounts/verify_otp.html')
        
        # Check if OTP is exactly 6 digits
        if not otp_input.isdigit() or len(otp_input) != 6:
            messages.error(request, 'Please enter a valid 6-digit OTP.')
            return render(request, 'accounts/verify_otp.html')
        
        # Check if user has an OTP stored
        if not user.otp:
            messages.error(request, 'No OTP found. Please request a new OTP.')
            return render(request, 'accounts/verify_otp.html')
        
        # Check if OTP has expired (10 minutes)
        if user.otp_created_at and (timezone.now() - user.otp_created_at).total_seconds() > 600:
            messages.error(request, 'OTP has expired. Please request a new OTP.')
            user.otp = ''
            user.save()
            return render(request, 'accounts/verify_otp.html')
        
        # Verify OTP
        if otp_input == user.otp:
            user.is_active = True
            user.is_verified = True
            user.otp = ''
            user.otp_created_at = None
            user.save()
            
            # Clear the session
            if 'pending_user_id' in request.session:
                del request.session['pending_user_id']
            
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
                
                # Send email with better formatting
                subject = 'Password Reset OTP - PaperSetu'
                message = f'''
Hello {user.get_full_name() or user.username},

You have requested to reset your password for your PaperSetu account.

Your OTP (One-Time Password) is: {otp}

This OTP is valid for 10 minutes. If you did not request this password reset, please ignore this email.

Best regards,
PaperSetu Team
                '''
                
                try:
                    send_mail(
                        subject,
                        message,
                        'papersetu@gmail.com',
                        [user.email],
                        fail_silently=False,
                    )
                    request.session['reset_user_id'] = user.id
                    messages.success(request, f'OTP has been sent to {email}. Please check your email.')
                    return redirect('accounts:password_reset_otp')
                except Exception as e:
                    messages.error(request, 'Failed to send OTP. Please try again later.')
                    # Clear the OTP if email fails
                    user.otp = ''
                    user.otp_created_at = None
                    user.save()
                    
            except ObjectDoesNotExist:
                messages.error(request, 'No user found with that email address.')
    else:
        form = PasswordResetEmailForm()
    return render(request, 'accounts/password_reset_email.html', {'form': form})

def password_reset_otp(request):
    user_id = request.session.get('reset_user_id')
    if not user_id:
        messages.error(request, 'Please request a password reset first.')
        return redirect('accounts:password_reset_request')
    
    try:
        user = User.objects.get(id=user_id)
    except ObjectDoesNotExist:
        messages.error(request, 'Invalid reset session. Please try again.')
        return redirect('accounts:password_reset_request')
    
    if request.method == 'POST':
        form = PasswordResetOTPForm(request.POST)
        if form.is_valid():
            otp_input = form.cleaned_data['otp']
            # OTP valid for 10 minutes
            if user.otp == otp_input and user.otp_created_at and (timezone.now() - user.otp_created_at).total_seconds() < 600:
                request.session['otp_verified'] = True
                messages.success(request, 'OTP verified successfully. Please set your new password.')
                return redirect('accounts:password_reset_new')
            else:
                if not user.otp or user.otp != otp_input:
                    messages.error(request, 'Invalid OTP. Please check and try again.')
                else:
                    messages.error(request, 'OTP has expired. Please request a new one.')
    else:
        form = PasswordResetOTPForm()
    return render(request, 'accounts/password_reset_otp.html', {'form': form})

def password_reset_new(request):
    user_id = request.session.get('reset_user_id')
    otp_verified = request.session.get('otp_verified')
    if not user_id or not otp_verified:
        messages.error(request, 'Please complete the OTP verification first.')
        return redirect('accounts:password_reset_request')
    
    try:
        user = User.objects.get(id=user_id)
    except ObjectDoesNotExist:
        messages.error(request, 'Invalid reset session. Please try again.')
        return redirect('accounts:password_reset_request')
    
    if request.method == 'POST':
        form = SetNewPasswordForm(user, request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data['new_password1'])
            user.otp = ''
            user.otp_created_at = None
            user.is_active = True
            user.is_verified = True
            user.save()
            # Clear session
            request.session.pop('reset_user_id', None)
            request.session.pop('otp_verified', None)
            messages.success(request, 'Password reset successful! You can now log in with your new password.')
            return redirect('accounts:login')
    else:
        form = SetNewPasswordForm(user)
    return render(request, 'accounts/password_reset_new.html', {'form': form}) 