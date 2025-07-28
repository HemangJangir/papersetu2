# PaperSetu Deployment Guide

## Overview
This guide covers deployment, database management, admin UI improvements, and login issue resolution for PaperSetu.

## 1. Database Management After Deployment

### Initial Setup Commands
After deploying to Render, run these commands in the Render shell:

```bash
# Check database status
python manage.py manage_production_db status

# Create superuser if needed
python manage.py manage_production_db create_superuser --username admin --email admin@papersetu.com --password admin123

# Add ICIMMI conference
python manage.py add_icimmi_conference

# Collect static files
python manage.py collectstatic --no-input

# Run migrations
python manage.py migrate
```

### Database Management Commands

#### Check Database Status
```bash
python manage.py manage_production_db status
```

#### Create Superuser
```bash
python manage.py manage_production_db create_superuser --username your_username --email your_email --password your_password
```

#### Backup Database (PostgreSQL only)
```bash
python manage.py manage_production_db backup
```

#### Check User Accounts
```bash
python manage.py manage_production_db check_users
```

#### Reset All Passwords
```bash
python manage.py manage_production_db reset_passwords
```

## 2. Admin UI Improvements

### Features Added:
- **Modern Admin Interface**: Using django-admin-interface
- **Custom Styling**: Professional blue theme
- **Enhanced Conference Management**: Better filtering and search
- **Quick Actions**: Direct links to papers, roles, and management
- **Statistics Display**: Conference statistics in admin
- **Bulk Actions**: Approve multiple conferences at once

### Admin Access:
- **URL**: `https://papersetu2.onrender.com/admin/`
- **Default Credentials**: 
  - Username: `admin`
  - Password: `admin123`

### Admin Features:
1. **Conference Management**:
   - Filter by status (Approved, Pending, Upcoming, Live, Completed)
   - Search by name, acronym, chair, venue
   - Quick approve buttons
   - Conference statistics
   - Direct links to papers and roles

2. **User Management**:
   - View all users with status indicators
   - Check user roles and permissions
   - Monitor user activity

3. **Paper Management**:
   - Track paper submissions
   - Monitor review status
   - View paper statistics

## 3. Login Issue Resolution

### Diagnose Login Problems
```bash
# General diagnosis
python manage.py fix_login_issues diagnose

# Check specific user
python manage.py fix_login_issues diagnose --username username_here

# Check by email
python manage.py fix_login_issues diagnose --email email@example.com
```

### Fix Common Issues

#### Activate Inactive Users
```bash
python manage.py fix_login_issues activate_users
```

#### Fix Password Issues
```bash
python manage.py fix_login_issues fix_passwords
```

#### Test Authentication
```bash
python manage.py fix_login_issues test_auth --username username_here
```

### Common Login Issues and Solutions

#### Issue 1: User Cannot Login
**Symptoms**: "Invalid credentials" error
**Solutions**:
1. Check if user exists: `python manage.py fix_login_issues diagnose --username username`
2. Activate user: `python manage.py fix_login_issues activate_users --username username`
3. Reset password: `python manage.py fix_login_issues fix_passwords --username username`

#### Issue 2: Email Login Not Working
**Symptoms**: Can login with username but not email
**Solutions**:
1. Check authentication backends are configured
2. Verify email format is valid
3. Test email authentication: `python manage.py fix_login_issues test_auth --username username`

#### Issue 3: Account Not Verified
**Symptoms**: User registered but cannot access features
**Solutions**:
1. Activate user: `python manage.py fix_login_issues activate_users --username username`
2. Mark as verified in admin panel

## 4. Production Environment Variables

### Required Environment Variables on Render:
```
DEBUG=False
DATABASE_URL=postgresql://...
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=papersetu2.onrender.com,*.onrender.com
```

### Optional Environment Variables:
```
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
STRIPE_SECRET_KEY=your-stripe-key
STRIPE_PUBLISHABLE_KEY=your-stripe-key
```

## 5. Monitoring and Maintenance

### Regular Maintenance Tasks

#### Daily:
- Check admin panel for new conferences
- Monitor user registrations
- Review error logs

#### Weekly:
- Backup database: `python manage.py manage_production_db backup`
- Check user accounts: `python manage.py manage_production_db check_users`
- Review conference statistics

#### Monthly:
- Update dependencies
- Review and clean up inactive users
- Check for security updates

### Performance Monitoring

#### Database Performance:
```bash
# Check database status
python manage.py manage_production_db status

# Monitor user growth
python manage.py manage_production_db check_users
```

#### Application Performance:
- Monitor Render dashboard for resource usage
- Check response times in admin panel
- Review error logs for issues

## 6. Troubleshooting

### Admin Panel Issues

#### Problem: Admin panel not styled
**Solution**:
```bash
python manage.py collectstatic --no-input
```

#### Problem: Admin panel not accessible
**Solution**:
1. Check if superuser exists: `python manage.py manage_production_db check_users`
2. Create superuser if needed: `python manage.py manage_production_db create_superuser`

### Database Issues

#### Problem: Database connection errors
**Solution**:
1. Check DATABASE_URL in environment variables
2. Verify PostgreSQL service is running on Render
3. Check database credentials

#### Problem: Missing data after deployment
**Solution**:
1. Run migrations: `python manage.py migrate`
2. Add missing data: `python manage.py add_icimmi_conference`
3. Check data integrity: `python manage.py manage_production_db status`

### Login Issues

#### Problem: Users cannot login
**Solution**:
1. Diagnose: `python manage.py fix_login_issues diagnose`
2. Activate users: `python manage.py fix_login_issues activate_users`
3. Fix passwords: `python manage.py fix_login_issues fix_passwords`

## 7. Security Best Practices

### Admin Security:
- Change default admin password immediately
- Use strong passwords for all admin accounts
- Regularly review admin access
- Monitor admin login attempts

### User Security:
- Implement password complexity requirements
- Enable email verification
- Monitor suspicious login attempts
- Regular security audits

## 8. Support and Contact

### For Technical Issues:
- Check Render logs for error messages
- Use management commands for diagnosis
- Review this deployment guide
- Contact development team with specific error messages

### Emergency Procedures:
1. **Database Issues**: Use backup and restore procedures
2. **Login Issues**: Use fix_login_issues commands
3. **Admin Access**: Create new superuser if needed
4. **Performance Issues**: Check Render dashboard and logs

---

**Last Updated**: December 2024
**Version**: 1.0 