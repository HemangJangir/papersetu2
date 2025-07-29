#!/usr/bin/env python
"""
Database Access Script for PaperSetu
This script helps you access your database and see all data.
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conference_mgmt.settings')
django.setup()

from accounts.models import User
from conference.models import Conference, Paper
from django.db.models import Count
from datetime import datetime

def print_separator(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

def main():
    print_separator("PAPERSETU DATABASE ACCESS")
    
    print("🔗 HOW TO ACCESS YOUR DATABASE:")
    print()
    print("1. ADMIN INTERFACE (Recommended):")
    print("   - Go to: https://your-domain.com/admin/")
    print("   - Login with your admin credentials")
    print("   - Navigate to Users and Conferences sections")
    print()
    print("2. MANAGEMENT COMMANDS:")
    print("   python manage.py list_all_conferences")
    print("   python manage.py list_all_users")
    print("   python check_database.py")
    print()
    print("3. DJANGO SHELL:")
    print("   python manage.py shell")
    print("   >>> from accounts.models import User")
    print("   >>> from conference.models import Conference")
    print("   >>> User.objects.all()")
    print("   >>> Conference.objects.all()")
    print()
    
    # Get basic statistics
    total_users = User.objects.count()
    total_conferences = Conference.objects.count()
    total_papers = Paper.objects.count()
    
    print("📊 CURRENT DATABASE STATISTICS:")
    print(f"   Total Users: {total_users}")
    print(f"   Total Conferences: {total_conferences}")
    print(f"   Total Papers: {total_papers}")
    
    # User statistics
    active_users = User.objects.filter(is_active=True).count()
    verified_users = User.objects.filter(is_verified=True).count()
    unverified_users = User.objects.filter(is_verified=False).count()
    
    print(f"\n👥 USER BREAKDOWN:")
    print(f"   Active Users: {active_users}")
    print(f"   Verified Users: {verified_users}")
    print(f"   Unverified Users: {unverified_users}")
    
    # Conference statistics
    approved_conferences = Conference.objects.filter(is_approved=True).count()
    pending_conferences = Conference.objects.filter(is_approved=False).count()
    
    print(f"\n🏢 CONFERENCE BREAKDOWN:")
    print(f"   Approved Conferences: {approved_conferences}")
    print(f"   Pending Conferences: {pending_conferences}")
    
    # Show recent users
    print_separator("RECENT USERS (Last 10)")
    recent_users = User.objects.order_by('-date_joined')[:10]
    for user in recent_users:
        user_name = user.get_full_name() or user.username
        status = "✓ Verified" if user.is_verified else "✗ Unverified"
        active = "✓ Active" if user.is_active else "✗ Inactive"
        print(f"{user.date_joined.strftime('%Y-%m-%d %H:%M')} - {user_name} ({user.email}) - {status} - {active}")
    
    # Show recent conferences
    print_separator("RECENT CONFERENCES (Last 10)")
    recent_conferences = Conference.objects.order_by('-id')[:10]
    for conf in recent_conferences:
        chair_name = conf.chair.get_full_name() or conf.chair.username if conf.chair else "No chair"
        approved = "✓ Approved" if conf.is_approved else "⏳ Pending"
        print(f"{conf.acronym} - {conf.name[:50]}... - {chair_name} - {approved}")
    
    print_separator("QUICK ACTIONS")
    print("To approve all pending conferences:")
    print("  python manage.py shell")
    print("  >>> from conference.models import Conference")
    print("  >>> Conference.objects.filter(is_approved=False).update(is_approved=True)")
    print()
    print("To verify all users:")
    print("  python manage.py shell")
    print("  >>> from accounts.models import User")
    print("  >>> User.objects.filter(is_verified=False).update(is_verified=True)")
    print()
    print("To see all conferences with details:")
    print("  python manage.py list_all_conferences")
    print()
    print("To see all users with details:")
    print("  python manage.py list_all_users")

if __name__ == "__main__":
    main() 