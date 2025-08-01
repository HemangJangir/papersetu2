# OTP Flow Fix Implementation

## Problem Description
The original OTP flow had several issues:
1. Users were created immediately during signup, even if they didn't complete OTP verification
2. Unverified users could still log in and appear as verified in the admin panel
3. Users couldn't re-register with the same email if they didn't complete OTP verification
4. No cleanup mechanism for abandoned registrations

## Solution Implemented

### 1. Enhanced Signup Process (`accounts/views.py` - CombinedAuthView.post)
- **Before**: User created immediately, regardless of OTP completion
- **After**: 
  - Check if user with email already exists
  - If exists and is verified → Show error "email already registered"
  - If exists but not verified → Delete old user and allow re-registration
  - Create new user with `is_verified=False`
  - Send OTP email
  - If email fails → Delete user and show error

### 2. Secure Login Process (`accounts/views.py` - CombinedAuthView.post)
- **Before**: Unverified users could log in and were auto-verified
- **After**:
  - Check if user is verified before allowing login
  - If not verified → Generate new OTP, send email, redirect to OTP page
  - If verified → Allow normal login
  - Clear error messages for invalid credentials

### 3. Improved OTP Verification (`accounts/views.py` - verify_otp)
- **Before**: Basic OTP verification
- **After**:
  - Check if user is already verified (prevent duplicate verification)
  - Better session handling
  - Clear session data on completion or error
  - Enhanced error messages

### 4. Automatic Cleanup System
- **Management Command**: `python manage.py cleanup_unverified_users`
  - Deletes unverified users older than 7 days (configurable)
  - Supports dry-run mode for testing
  - Can be scheduled via cron job

- **Signal-based Cleanup**: `accounts/signals.py`
  - Automatically cleans up old unverified users every 10 minutes
  - Runs when any user is saved (performance-optimized)

### 5. New Files Created
- `accounts/apps.py` - App configuration with signal registration
- `accounts/signals.py` - Automatic cleanup signals
- `accounts/management/commands/cleanup_unverified_users.py` - Management command
- `OTP_FLOW_FIX.md` - This documentation

## Flow Summary

### New User Registration:
1. User fills signup form
2. System checks for existing user with same email
3. If verified user exists → Error message
4. If unverified user exists → Delete old user
5. Create new user with `is_verified=False`
6. Send OTP email
7. Redirect to OTP verification page

### OTP Verification:
1. User enters OTP
2. If correct → Set `is_verified=True`, log user in
3. If incorrect → Show error, allow retry
4. If expired → Allow resend OTP

### Login Attempt:
1. User enters credentials
2. If user not verified → Generate new OTP, send email, redirect to verification
3. If user verified → Allow normal login
4. If invalid credentials → Show error message

### Cleanup:
1. Automatic cleanup every 10 minutes via signals
2. Manual cleanup via management command
3. Unverified users older than 7 days are deleted

## Usage

### Manual Cleanup:
```bash
# Dry run to see what would be deleted
python manage.py cleanup_unverified_users --dry-run

# Actually delete old unverified users
python manage.py cleanup_unverified_users

# Delete users older than 3 days
python manage.py cleanup_unverified_users --days 3
```

### Scheduled Cleanup (cron):
```bash
# Add to crontab to run daily at 2 AM
0 2 * * * cd /path/to/project && python manage.py cleanup_unverified_users
```

## Benefits
1. **Security**: Unverified users cannot access the system
2. **User Experience**: Clear error messages and proper flow
3. **Database Cleanliness**: Automatic cleanup of abandoned registrations
4. **Re-registration**: Users can re-register if they don't complete OTP
5. **Admin Accuracy**: Admin panel shows correct verification status

## Testing
- Test signup with existing verified email → Should show error
- Test signup with existing unverified email → Should allow re-registration
- Test login with unverified user → Should redirect to OTP
- Test OTP verification → Should work correctly and auto-login user
- Test cleanup command → Should remove old unverified users

## Recent Fixes (Latest Update)
- **Auto-login after OTP verification**: Users are now automatically logged in after successful OTP verification
- **Session flags**: Added `login_verification` flag to distinguish between new registration and login verification
- **Welcome email**: Only sent for new registrations, not for login verification
- **Form validation**: Updated to allow re-registration for unverified users
- **Cleanup tested**: Successfully cleaned up old unverified users 