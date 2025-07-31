from django import forms
from django.contrib.auth.forms import UserCreationForm, SetPasswordForm
from .models import User

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400',
        'placeholder': 'Enter your email',
    }))
    first_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={
        'class': 'w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400',
        'placeholder': 'First name',
    }))
    last_name = forms.CharField(max_length=30, required=True, widget=forms.TextInput(attrs={
        'class': 'w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400',
        'placeholder': 'Last name',
    }))
    username = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={
        'class': 'w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400',
        'placeholder': 'Username',
    }))
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput(attrs={
        'class': 'w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400',
        'placeholder': 'Password',
    }))
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput(attrs={
        'class': 'w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400',
        'placeholder': 'Confirm password',
    }))

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'password1', 'password2']

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('A user with that username already exists.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        
        # Check if user already exists
        existing_user = User.objects.filter(email=email).first()
        
        if existing_user:
            # User already exists - prevent duplicate registration
            try:
                from conference.models import PCInvite
                pc_invites = PCInvite.objects.filter(email=email)
                
                if pc_invites.exists():
                    # Get conference names for better error message
                    conference_names = [invite.conference.name for invite in pc_invites]
                    conferences_text = ', '.join(conference_names)
                    raise forms.ValidationError(
                        f'This email is already registered. You have PC member invitations for: {conferences_text}. '
                        f'Please try logging in with your existing account, or use "Forgot Password" if needed.'
                    )
                else:
                    raise forms.ValidationError('A user with that email already exists. Please try logging in instead.')
            except ImportError:
                raise forms.ValidationError('A user with that email already exists. Please try logging in instead.')
        
        # If no existing user, check for PC invites to allow registration
        try:
            from conference.models import PCInvite
            pc_invites = PCInvite.objects.filter(email=email)
            if pc_invites.exists():
                # Store PC invites info for later linking during registration
                self.pc_invites = pc_invites
        except ImportError:
            pass
            
        return email

    def clean(self):
        cleaned_data = super().clean()
        # Check password validation first before checking username/email uniqueness
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError("The two password fields didn't match.")
            
            # Check password strength
            if len(password1) < 8:
                raise forms.ValidationError("Password must be at least 8 characters long.")
            
            if password1.isdigit():
                raise forms.ValidationError("Password cannot be entirely numeric.")
            
            if password1.lower() in ['password', '123456', '12345678', 'qwerty', 'abc123', 'password123']:
                raise forms.ValidationError("This password is too common. Please choose a stronger password.")
        
        return cleaned_data

class PasswordResetEmailForm(forms.Form):
    email = forms.EmailField(
        label='Email', 
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400',
            'placeholder': 'Enter your email address',
        })
    )

class PasswordResetOTPForm(forms.Form):
    otp = forms.CharField(
        label='OTP', 
        max_length=6, 
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400',
            'placeholder': 'Enter 6-digit OTP',
            'pattern': '[0-9]{6}',
            'maxlength': '6',
        })
    )

class SetNewPasswordForm(SetPasswordForm):
    def __init__(self, user, *args, **kwargs):
        super().__init__(user, *args, **kwargs)
        self.fields['new_password1'].widget.attrs.update({
            'class': 'w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400',
            'placeholder': 'Enter new password',
        })
        self.fields['new_password2'].widget.attrs.update({
            'class': 'w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400',
            'placeholder': 'Confirm new password',
        }) 