# PC Invite Registration Solution

## 🎯 **Problem Statement**
When users receive PC member invitations, they can either:
1. **Accept the invite first** (via email link), then try to register
2. **Register first**, then accept the invite later

Both scenarios can cause issues with the current system.

## 🚀 **Solution Overview**

### **Scenario 1: Accept Invite → Register**
- ✅ **Allow registration** for users with accepted PC invites
- ✅ **Auto-link** their account to the accepted invites
- ✅ **Create PC member roles** automatically

### **Scenario 2: Register → Accept Invite**
- ✅ **Auto-accept** pending invites during registration
- ✅ **Update invite status** to accepted
- ✅ **Create PC member roles** automatically

### **Scenario 3: Already Registered**
- ❌ **Prevent duplicate registration**
- ✅ **Provide helpful error message** with conference names
- ✅ **Guide to login or password reset**

## 📋 **Implementation Details**

### **1. Smart Form Validation (`accounts/forms.py`)**
```python
def clean_email(self):
    email = self.cleaned_data.get('email')
    
    # Check if user already exists
    existing_user = User.objects.filter(email=email).first()
    
    if existing_user:
        # Prevent duplicate registration with helpful message
        # Show conference names if PC invites exist
    else:
        # Allow registration for users with PC invites
        # Store PC invites info for later linking
```

### **2. Registration Process (`accounts/views.py`)**
```python
def link_pc_invites(self, user, form):
    # Handle both scenarios:
    # - Pending invites: Auto-accept and create roles
    # - Accepted invites: Just create roles
```

### **3. Management Command (`accounts/management/commands/link_pc_invites.py`)**
```bash
# Link all existing users with PC invites
python manage.py link_pc_invites

# Link specific email
python manage.py link_pc_invites --email user@example.com

# Dry run to see what would be done
python manage.py link_pc_invites --dry-run
```

## 🔄 **User Flow Examples**

### **Flow 1: Accept Invite → Register**
1. User receives PC invite email
2. User clicks "Accept" link → Invite status: "accepted"
3. User visits website and registers
4. System detects accepted invites
5. System creates account and links PC roles
6. User can access conference as PC member

### **Flow 2: Register → Accept Invite**
1. User receives PC invite email
2. User visits website and registers first
3. System detects pending invites
4. System auto-accepts invites and creates PC roles
5. User clicks "Accept" link (already accepted)
6. User can access conference as PC member

### **Flow 3: Already Registered**
1. User receives PC invite email
2. User tries to register with existing email
3. System shows error: "Email already registered. You have PC member invitations for: Conference Name. Please try logging in."
4. User logs in with existing account
5. User can access conference as PC member

## 🛠️ **Usage Instructions**

### **For New Users:**
1. **Register normally** - system will handle invite linking automatically
2. **Check your dashboard** - PC member roles will be visible
3. **Access conferences** - you'll have PC member permissions

### **For Existing Users:**
1. **Try logging in** with your existing account
2. **Use "Forgot Password"** if you can't remember password
3. **Contact conference chairs** if you need help

### **For Administrators:**
1. **Run management command** to link existing users:
   ```bash
   python manage.py link_pc_invites
   ```
2. **Check admin panel** for PC member assignments
3. **Monitor notifications** for accepted invites

## ✅ **Benefits**

1. **Seamless Experience**: Users can register regardless of invite order
2. **Automatic Linking**: No manual intervention required
3. **Clear Messaging**: Users understand what's happening
4. **Backward Compatible**: Works with existing invites
5. **Admin Friendly**: Easy to manage and monitor

## 🔧 **Technical Notes**

- **Database Integrity**: Maintains referential integrity
- **Error Handling**: Graceful fallbacks for missing apps
- **Notifications**: Automatic notifications to chairs
- **Role Management**: Proper PC member role assignment
- **Track Support**: Handles track-specific invitations

## 🚨 **Important Notes**

1. **Test thoroughly** before production deployment
2. **Monitor invite status** in admin panel
3. **Backup database** before running management commands
4. **Check logs** for any errors during linking
5. **Delete temporary views** after use

## 📞 **Support**

If users encounter issues:
1. **Check admin panel** for user and invite status
2. **Run management command** to fix linking issues
3. **Contact support** with specific error messages
4. **Provide conference names** for better assistance

## 🔍 **Testing Scenarios**

### **Test Case 1: Accept First**
1. Send PC invite to test@example.com
2. Accept invite via email link
3. Try to register with test@example.com
4. Verify PC member role is created

### **Test Case 2: Register First**
1. Send PC invite to test@example.com
2. Register with test@example.com first
3. Accept invite via email link
4. Verify PC member role is created

### **Test Case 3: Already Registered**
1. Create user with test@example.com
2. Send PC invite to test@example.com
3. Try to register with test@example.com
4. Verify helpful error message appears 