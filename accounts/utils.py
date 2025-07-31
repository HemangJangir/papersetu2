from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import random
import string

User = get_user_model()

def invite_user_by_email(email, name=None, role_type="PC Member"):
    """
    Create a user account for an invited person and send them a password reset email.
    
    Args:
        email (str): The email address of the invited person
        name (str, optional): The name of the invited person
        role_type (str): Type of role (PC Member, Subreviewer, etc.)
    
    Returns:
        tuple: (user, created) - user object and whether it was created
    """
    # Generate a username if name is provided, otherwise use email prefix
    if name:
        # Create username from name (first letter of first name + last name)
        name_parts = name.strip().split()
        if len(name_parts) >= 2:
            username = f"{name_parts[0][0].lower()}{name_parts[-1].lower()}"
        else:
            username = name_parts[0].lower()
    else:
        # Use email prefix as username
        username = email.split('@')[0]
    
    # Ensure username is unique
    base_username = username
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1
    
    # Create user if it doesn't exist
    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            'username': username,
            'first_name': name.split()[0] if name and ' ' in name else name or '',
            'last_name': ' '.join(name.split()[1:]) if name and len(name.split()) > 1 else '',
            'is_active': True,
            'is_verified': True,
        }
    )
    
    if created:
        # Set unusable password to prevent login until they set one
        user.set_unusable_password()
        user.save()
        
        # Send password reset email
        send_password_reset_email(user, role_type)
        
        return user, True
    else:
        # User already exists, send password reset email anyway
        send_password_reset_email(user, role_type)
        return user, False

def send_password_reset_email(user, role_type="PC Member"):
    """
    Send a password reset email to the user.
    
    Args:
        user: User object
        role_type (str): Type of role they were invited for
    """
    try:
        # Use Django's built-in password reset form
        form = PasswordResetForm({'email': user.email})
        if form.is_valid():
            # Generate password reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Create password reset URL
            reset_url = f"{settings.SITE_URL}/accounts/password-reset-confirm/{uid}/{token}/"
            
            # Send email
            subject = f'Set Your Password - PaperSetu {role_type} Invitation'
            message = f'''
Hello {user.get_full_name() or user.username},

You have been invited to join PaperSetu as a {role_type}.

To get started, please set your password by clicking the link below:

{reset_url}

This link will expire in 24 hours. If you did not expect this invitation, please ignore this email.

Your username is: {user.username}

Best regards,
PaperSetu Team
            '''
            
            send_mail(
                subject,
                message,
                'noreply@papersetu.com',
                [user.email],
                fail_silently=False,
            )
            
            return True
    except Exception as e:
        print(f"Error sending password reset email: {e}")
        return False

def get_or_create_invited_user(email, name=None, role_type="PC Member"):
    """
    Get existing user or create new one for invitation.
    This is a wrapper that handles both cases.
    
    Returns:
        tuple: (user, created, action_taken)
        - user: User object
        - created: Whether user was created
        - action_taken: What action was taken ('created', 'exists_sent_reset', 'exists_no_action')
    """
    try:
        user = User.objects.get(email=email)
        
        # User exists, check if they have a usable password
        if user.has_usable_password():
            # User has password, no action needed
            return user, False, 'exists_no_action'
        else:
            # User exists but no password, send reset email
            send_password_reset_email(user, role_type)
            return user, False, 'exists_sent_reset'
            
    except User.DoesNotExist:
        # User doesn't exist, create new one
        user, created = invite_user_by_email(email, name, role_type)
        return user, created, 'created' 