#!/usr/bin/env python
"""
Database Check Script for PaperSetu
This script helps you check your database and see all conferences and users.
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
    print_separator("PAPERSETU DATABASE CHECK")
    
    # Get basic statistics
    total_users = User.objects.count()
    total_conferences = Conference.objects.count()
    total_papers = Paper.objects.count()
    
    print(f"📊 DATABASE OVERVIEW:")
    print(f"   Total Users: {total_users}")
    print(f"   Total Conferences: {total_conferences}")
    print(f"   Total Papers: {total_papers}")
    
    # User statistics
    active_users = User.objects.filter(is_active=True).count()
    verified_users = User.objects.filter(is_verified=True).count()
    recent_users = User.objects.filter(date_joined__gte=datetime.now().replace(day=datetime.now().day-7)).count()
    
    print(f"\n👥 USER STATISTICS:")
    print(f"   Active Users: {active_users}")
    print(f"   Verified Users: {verified_users}")
    print(f"   Users Registered (Last 7 days): {recent_users}")
    
    # Conference statistics
    approved_conferences = Conference.objects.filter(is_approved=True).count()
    pending_conferences = Conference.objects.filter(is_approved=False).count()
    
    print(f"\n🏢 CONFERENCE STATISTICS:")
    print(f"   Approved Conferences: {approved_conferences}")
    print(f"   Pending Conferences: {pending_conferences}")
    
    # Status breakdown
    status_counts = Conference.objects.values('status').annotate(count=Count('id'))
    print(f"   Status Breakdown:")
    for status in status_counts:
        print(f"     {status['status'].title()}: {status['count']}")
    
    print_separator("RECENT USERS (Last 10)")
    
    recent_users = User.objects.order_by('-date_joined')[:10]
    for user in recent_users:
        user_name = user.get_full_name() or user.username
        conference_count = user.conference_set.count()
        paper_count = user.paper_set.count()
        
        activity = []
        if conference_count > 0:
            activity.append(f"{conference_count} conf")
        if paper_count > 0:
            activity.append(f"{paper_count} papers")
        
        activity_str = f" ({', '.join(activity)})" if activity else ""
        print(f"{user.date_joined.strftime('%Y-%m-%d %H:%M')} - {user_name}{activity_str}")
    
    print_separator("RECENT CONFERENCES (Last 10)")
    
    recent_conferences = Conference.objects.order_by('-id')[:10]
    for conf in recent_conferences:
        chair_name = conf.chair.get_full_name() or conf.chair.username if conf.chair else "No chair"
        status_icon = "✓" if conf.is_approved else "⏳"
        print(f"{status_icon} {conf.acronym} ({conf.status}) - {conf.name[:60]}... by {chair_name}")
    
    print_separator("ADMIN ACCESS INFORMATION")
    
    print("🔗 ADMIN INTERFACE LINKS:")
    print("   Main Admin: http://your-domain.com/admin/")
    print("   Users: http://your-domain.com/admin/accounts/user/")
    print("   Conferences: http://your-domain.com/admin/conference/conference/")
    print("   Papers: http://your-domain.com/admin/conference/paper/")
    
    print("\n📋 MANAGEMENT COMMANDS:")
    print("   List all conferences: python manage.py list_all_conferences")
    print("   List all users: python manage.py list_all_users")
    print("   List pending conferences: python manage.py list_all_conferences --pending")
    print("   List recent users: python manage.py list_all_users --recent 7")
    
    print("\n⚡ QUICK ACTIONS:")
    print("   To approve all pending conferences:")
    print("     python manage.py shell")
    print("     >>> from conference.models import Conference")
    print("     >>> Conference.objects.filter(is_approved=False).update(is_approved=True)")
    
    print("\n   To verify all users:")
    print("     python manage.py shell")
    print("     >>> from accounts.models import User")
    print("     >>> User.objects.filter(is_verified=False).update(is_verified=True)")
    
    print_separator("DATABASE DETAILS")
    
    # Show some detailed information
    if total_conferences > 0:
        print("🏢 CONFERENCE DETAILS:")
        for conf in Conference.objects.all()[:5]:  # Show first 5
            chair_name = conf.chair.get_full_name() or conf.chair.username if conf.chair else "No chair"
            paper_count = conf.papers.count()
            user_count = conf.userconferencerole_set.count()
            print(f"   {conf.acronym}: {conf.name}")
            print(f"     Chair: {chair_name}")
            print(f"     Status: {conf.status} ({'Approved' if conf.is_approved else 'Pending'})")
            print(f"     Papers: {paper_count}, Users: {user_count}")
            print(f"     Dates: {conf.start_date} to {conf.end_date}")
            print()
    
    if total_users > 0:
        print("👥 USER DETAILS:")
        for user in User.objects.all()[:5]:  # Show first 5
            user_name = user.get_full_name() or user.username
            conference_count = user.conference_set.count()
            paper_count = user.paper_set.count()
            print(f"   {user_name} ({user.email})")
            print(f"     Status: {'Active' if user.is_active else 'Inactive'} ({'Verified' if user.is_verified else 'Not Verified'})")
            print(f"     Joined: {user.date_joined.strftime('%Y-%m-%d')}")
            print(f"     Activity: {conference_count} conferences, {paper_count} papers")
            print()

if __name__ == "__main__":
    main() 