# Invite User Solution - PC Members & Subreviewers

## 🎯 **Problem Statement**
When inviting someone as a PC member or subreviewer, the system should:
1. **Create a user account** automatically with their email
2. **Set an unusable password** to prevent login until they set one
3. **Send a password reset email** using Django's built-in system
4. **Handle registration conflicts** when invited users try to register

## 🚀 **Solution Overview**

### **For PC Members:**
- ✅ **Auto-create user account** when sending PC invite
- ✅ **Set unusable password** to block login
- ✅ **Send password reset email** with username
- ✅ **Handle registration conflicts** gracefully

### **For Subreviewers:**
- ✅ **Select from existing users** (current system works)
- ✅ **No changes needed** for subreviewer invites

## 📋 **Implementation Details**

### **1. Utility Functions (`accounts/utils.py`)**

#### **`invite_user_by_email(email, name, role_type)`**
- Creates user account if not exists
- Generates username from name or email
- Sets unusable password
- Sends password reset email

#### **`send_password_reset_email(user, role_type)`**
- Uses Django's built-in password reset system
- Generates secure reset token
- Sends email with reset link and username

#### **`get_or_create_invited_user(email, name, role_type)`**
- Wrapper function that handles all scenarios
- Returns user object and action taken

### **2. PC Invite Creation (`dashboard/views.py`)**

#### **Updated PC Invite Process:**
```python
# Create or get user account for the invited person
from accounts.utils import get_or_create_invited_user
user, created, action_taken = get_or_create_invited_user(
    email=email, 
    name=name, 
    role_type="PC Member"
)

# Create PC invite
invite = PCInvite.objects.create(...)

# Send invitation email with username info
if action_taken == 'created':
    password_info = f"Account created with username: {user.username}"
elif action_taken == 'exists_sent_reset':
    password_info = f"Password reset sent for username: {user.username}"
```

### **3. Registration Form (`accounts/forms.py`)**

#### **Smart Email Validation:**
- **Existing user with pending invites**: Show helpful message
- **Existing user with accepted invites**: Guide to login/reset
- **No user with accepted invites**: Allow registration
- **No user, no invites**: Allow registration

### **4. Registration Process (`accounts/views.py`)**

#### **Auto-Link PC Invites:**
- **Pending invites**: Auto-accept and create roles
- **Accepted invites**: Just create roles
- **Send notifications** to chairs

## 🔄 **User Flow**

### **Flow 1: PC Member Invitation**
1. **Chair invites PC member** by email
2. **System creates user account** with unusable password
3. **System sends invitation email** with username
4. **System sends password reset email** separately
5. **User clicks password reset link** and sets password
6. **User accepts PC invitation** via email link
7. **User can access conference** as PC member

### **Flow 2: User Tries to Register After Accepting Invite**
1. **User accepts PC invitation** via email
2. **User tries to register** on website
3. **System detects accepted invites** and allows registration
4. **System links account** to accepted invites
5. **User can access conference** as PC member

### **Flow 3: User Already Has Account**
1. **User tries to register** with existing email
2. **System shows helpful message** with conference names
3. **User logs in** with existing account
4. **User can access conference** as PC member

## 🛠️ **Usage Instructions**

### **For Conference Chairs:**

#### **Inviting PC Members:**
1. **Go to PC Management** in conference dashboard
2. **Enter name and email** of PC member
3. **Click "Send Invitation"**
4. **System will:**
   - Create user account automatically
   - Send invitation email with username
   - Send password reset email
   - Show success message with details

#### **What the Invited Person Receives:**
1. **Invitation email** with conference details and username
2. **Password reset email** with link to set password
3. **Clear instructions** on how to proceed

### **For Invited Users:**

#### **First Time Setup:**
1. **Check email** for invitation and password reset
2. **Click password reset link** to set password
3. **Accept invitation** via email link
4. **Login to PaperSetu** with username and password
5. **Access conference dashboard** as PC member

#### **If You Already Have an Account:**
1. **Try logging in** with existing credentials
2. **Use "Forgot Password"** if needed
3. **Contact conference chair** if you need help

## 📧 **Email Templates**

### **PC Invitation Email:**
```
Dear [Name],

You have been invited to serve as a Program Committee (PC) member for the conference "[Conference Name]".

A PaperSetu account has been created for you with username: [username]
You will receive a separate email to set your password.

Please click the following link to accept or decline this invitation:
[Accept Link]

Best regards,
[Chair Name]
Conference Chair
```

### **Password Reset Email:**
```
Hello [Name],

You have been invited to join PaperSetu as a PC Member.

To get started, please set your password by clicking the link below:

[Password Reset Link]

This link will expire in 24 hours. If you did not expect this invitation, please ignore this email.

Your username is: [username]

Best regards,
PaperSetu Team
```

## 🔧 **Technical Notes**

### **Username Generation:**
- **From name**: First letter of first name + last name (e.g., "John Doe" → "jdoe")
- **From email**: Email prefix (e.g., "john.doe@example.com" → "john.doe")
- **Uniqueness**: Adds numbers if username exists (e.g., "jdoe1", "jdoe2")

### **Password Security:**
- **Unusable password**: Prevents login until user sets password
- **Secure reset tokens**: Uses Django's built-in token generator
- **24-hour expiration**: Standard Django password reset timeout

### **Database Integrity:**
- **User accounts**: Created with proper validation
- **PC invites**: Linked to user accounts
- **Conference roles**: Created automatically
- **Notifications**: Sent to chairs

## 🚨 **Important Notes**

### **For Development:**
1. **Test email sending** with console backend
2. **Check username generation** with various names
3. **Verify password reset flow** works correctly
4. **Test registration conflicts** with existing users

### **For Production:**
1. **Configure email settings** properly
2. **Set SITE_URL** environment variable
3. **Monitor email delivery** and failures
4. **Check user creation** in admin panel

### **Security Considerations:**
1. **Password reset tokens** are secure and time-limited
2. **Username generation** is deterministic and unique
3. **Email validation** prevents duplicate accounts
4. **Role assignment** is automatic and secure

## 📞 **Support**

### **Common Issues:**

#### **"Email already exists" error:**
- **Solution**: User should login with existing account
- **Alternative**: Use "Forgot Password" to reset

#### **Password reset email not received:**
- **Check**: Email settings and spam folder
- **Solution**: Contact admin to resend invitation

#### **Username not working:**
- **Check**: Email for correct username
- **Solution**: Use email address to login instead

#### **Invitation link expired:**
- **Solution**: Contact conference chair for new invitation

### **For Administrators:**
1. **Check admin panel** for user accounts
2. **Monitor PC invites** and their status
3. **Resend invitations** if needed
4. **Help users** with login issues 