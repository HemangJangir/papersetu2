from django.contrib import admin
from .models import Conference, ReviewerPool, ReviewInvite, UserConferenceRole, Paper, Review, Track
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.contrib.admin import SimpleListFilter

class ConferenceStatusFilter(SimpleListFilter):
    title = 'Conference Status'
    parameter_name = 'conference_status'

    def lookups(self, request, model_admin):
        return (
            ('approved', 'Approved'),
            ('pending', 'Pending Approval'),
            ('upcoming', 'Upcoming'),
            ('live', 'Live'),
            ('completed', 'Completed'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'approved':
            return queryset.filter(is_approved=True)
        elif self.value() == 'pending':
            return queryset.filter(is_approved=False)
        elif self.value() == 'upcoming':
            return queryset.filter(status='upcoming')
        elif self.value() == 'live':
            return queryset.filter(status='live')
        elif self.value() == 'completed':
            return queryset.filter(status='completed')

class ConferenceAdmin(admin.ModelAdmin):
    list_display = ('name', 'acronym', 'chair_info', 'status_display', 'approval_status', 'dates_display', 'conference_actions')
    list_filter = (ConferenceStatusFilter, 'primary_area', 'start_date', 'is_approved', 'status')
    search_fields = ('name', 'acronym', 'chair__username', 'chair__email', 'chair__first_name', 'chair__last_name', 'theme_domain', 'venue', 'city')
    list_per_page = 25
    date_hierarchy = 'start_date'
    readonly_fields = ('created_at', 'conference_stats', 'chair_info_display')
    list_editable = ('status',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'acronym', 'description', 'theme_domain'),
            'classes': ('wide',)
        }),
        ('Dates & Venue', {
            'fields': ('start_date', 'end_date', 'venue', 'city', 'country'),
            'classes': ('wide',)
        }),
        ('Organization', {
            'fields': ('chair', 'chair_name', 'chair_email', 'organizer', 'organizer_web_page'),
            'classes': ('wide',)
        }),
        ('Settings', {
            'fields': ('is_approved', 'status', 'primary_area', 'secondary_area', 'area_notes'),
            'classes': ('wide',)
        }),
        ('Submission Settings', {
            'fields': ('paper_submission_deadline', 'paper_format', 'abstract_required', 'max_paper_length'),
            'classes': ('wide',)
        }),
        ('Contact Information', {
            'fields': ('contact_email', 'contact_phone', 'web_page'),
            'classes': ('wide',)
        }),
        ('Statistics', {
            'fields': ('conference_stats',),
            'classes': ('collapse',)
        }),
    )

    def chair_info(self, obj):
        if obj.chair:
            return format_html(
                '<div style="min-width: 150px;">'
                '<strong>{}</strong><br>'
                '<small style="color: #666;">{}</small><br>'
                '<small style="color: #666;">{}</small>'
                '</div>',
                obj.chair.get_full_name() or obj.chair.username,
                obj.chair.email,
                f"Created: {obj.chair.date_joined.strftime('%Y-%m-%d')}"
            )
        return "No chair assigned"
    chair_info.short_description = 'Conference Chair'

    def chair_info_display(self, obj):
        if obj.chair:
            return format_html(
                '<div style="background: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #e9ecef;">'
                '<h4 style="margin-top: 0; color: #495057;">Chair Information</h4>'
                '<p><strong>Name:</strong> {}</p>'
                '<p><strong>Username:</strong> {}</p>'
                '<p><strong>Email:</strong> {}</p>'
                '<p><strong>Date Joined:</strong> {}</p>'
                '<p><strong>Last Login:</strong> {}</p>'
                '<p><strong>Account Status:</strong> <span style="color: {};">{}</span></p>'
                '</div>',
                obj.chair.get_full_name() or "Not provided",
                obj.chair.username,
                obj.chair.email,
                obj.chair.date_joined.strftime('%Y-%m-%d %H:%M'),
                obj.chair.last_login.strftime('%Y-%m-%d %H:%M') if obj.chair.last_login else "Never",
                "#28a745" if obj.chair.is_active else "#dc3545",
                "Active" if obj.chair.is_active else "Inactive"
            )
        return "No chair assigned"
    chair_info_display.short_description = 'Chair Details'

    def status_display(self, obj):
        status_colors = {
            'upcoming': '#007bff',
            'live': '#28a745',
            'completed': '#6c757d',
            'cancelled': '#dc3545',
        }
        color = status_colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="color: {}; font-weight: 600; padding: 4px 8px; border-radius: 4px; background: rgba(0,0,0,0.05);">'
            '{}'
            '</span>',
            color, obj.status.title()
        )
    status_display.short_description = 'Status'

    def approval_status(self, obj):
        if obj.is_approved:
            return format_html(
                '<span style="color: #28a745; font-weight: 600;">✓ Approved</span>'
            )
        else:
            return format_html(
                '<span style="color: #ffc107; font-weight: 600;">⏳ Pending</span>'
            )
    approval_status.short_description = 'Approval'

    def dates_display(self, obj):
        return format_html(
            '<div style="min-width: 120px;">'
            '<strong>Start:</strong> {}<br>'
            '<strong>End:</strong> {}<br>'
            '<small style="color: #666;">Deadline: {}</small>'
            '</div>',
            obj.start_date.strftime('%Y-%m-%d'),
            obj.end_date.strftime('%Y-%m-%d'),
            obj.paper_submission_deadline.strftime('%Y-%m-%d') if obj.paper_submission_deadline else "Not set"
        )
    dates_display.short_description = 'Dates'

    def approve_conference(self, obj):
        if not obj.is_approved:
            return format_html(
                '<a class="button" style="background-color: #28a745; color: white; padding: 5px 10px; text-decoration: none; border-radius: 3px;" href="/admin/conference/conference/{}/approve/">✓ Approve</a>', 
                obj.id
            )
        return format_html('<span style="color: green; font-weight: bold;">✓ Approved</span>')
    approve_conference.short_description = 'Approve Conference'
    approve_conference.allow_tags = True

    def conference_actions(self, obj):
        actions = []
        actions.append(f'<a href="/admin/conference/paper/?conference__id__exact={obj.id}" style="color: #007bff; text-decoration: none; margin-right: 10px;">📄 Papers</a>')
        actions.append(f'<a href="/admin/conference/userconferencerole/?conference__id__exact={obj.id}" style="color: #007bff; text-decoration: none; margin-right: 10px;">👥 Roles</a>')
        actions.append(f'<a href="/dashboard/conference_submissions/{obj.id}/" style="color: #28a745; text-decoration: none; margin-right: 10px;">🔧 Manage</a>')
        actions.append(f'<a href="/admin/conference/conference/{obj.id}/change/" style="color: #6c757d; text-decoration: none;">✏️ Edit</a>')
        return mark_safe(''.join(actions))
    conference_actions.short_description = 'Actions'

    def conference_stats(self, obj):
        if not obj.pk:
            return "Save the conference first to see statistics"
        
        paper_count = obj.papers.count()
        user_count = obj.userconferencerole_set.count()
        review_count = Review.objects.filter(paper__conference=obj).count()
        
        # Get recent activity
        recent_papers = obj.papers.order_by('-created_at')[:5]
        recent_roles = obj.userconferencerole_set.order_by('-created_at')[:5]
        
        stats_html = format_html(
            '<div style="background: #f8f9fa; padding: 20px; border-radius: 8px; border: 1px solid #e9ecef;">'
            '<h4 style="margin-top: 0; color: #495057; border-bottom: 2px solid #dee2e6; padding-bottom: 10px;">Conference Statistics</h4>'
            '<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 20px;">'
            '<div style="text-align: center; padding: 15px; background: white; border-radius: 6px; border: 1px solid #dee2e6;">'
            '<div style="font-size: 24px; font-weight: bold; color: #007bff;">{}</div>'
            '<div style="color: #6c757d; font-size: 14px;">Papers</div>'
            '</div>'
            '<div style="text-align: center; padding: 15px; background: white; border-radius: 6px; border: 1px solid #dee2e6;">'
            '<div style="font-size: 24px; font-weight: bold; color: #28a745;">{}</div>'
            '<div style="color: #6c757d; font-size: 14px;">Users</div>'
            '</div>'
            '<div style="text-align: center; padding: 15px; background: white; border-radius: 6px; border: 1px solid #dee2e6;">'
            '<div style="font-size: 24px; font-weight: bold; color: #ffc107;">{}</div>'
            '<div style="color: #6c757d; font-size: 14px;">Reviews</div>'
            '</div>'
            '</div>',
            paper_count, user_count, review_count
        )
        
        # Add recent activity
        if recent_papers or recent_roles:
            stats_html += format_html('<h5 style="color: #495057; margin-top: 20px;">Recent Activity</h5>')
            
            if recent_papers:
                stats_html += format_html('<div style="margin-bottom: 15px;"><strong>Recent Papers:</strong></div>')
                for paper in recent_papers:
                    stats_html += format_html(
                        '<div style="padding: 8px; background: white; border-radius: 4px; margin-bottom: 5px; border-left: 3px solid #007bff;">'
                        '<strong>{}</strong> by {} ({})'
                        '</div>',
                        paper.title[:50] + "..." if len(paper.title) > 50 else paper.title,
                        paper.author.get_full_name() or paper.author.username,
                        paper.created_at.strftime('%Y-%m-%d')
                    )
            
            if recent_roles:
                stats_html += format_html('<div style="margin-top: 15px; margin-bottom: 15px;"><strong>Recent Users:</strong></div>')
                for role in recent_roles:
                    stats_html += format_html(
                        '<div style="padding: 8px; background: white; border-radius: 4px; margin-bottom: 5px; border-left: 3px solid #28a745;">'
                        '<strong>{}</strong> - {} ({})'
                        '</div>',
                        role.user.get_full_name() or role.user.username,
                        role.get_role_display(),
                        role.created_at.strftime('%Y-%m-%d')
                    )
        
        return stats_html
    conference_stats.short_description = 'Statistics'

    actions = ['approve_selected_conferences', 'mark_as_upcoming', 'mark_as_live', 'mark_as_completed']

    def mark_as_upcoming(self, request, queryset):
        updated = queryset.update(status='upcoming')
        self.message_user(request, f'{updated} conferences marked as upcoming.')
    mark_as_upcoming.short_description = "Mark selected conferences as upcoming"

    def mark_as_live(self, request, queryset):
        updated = queryset.update(status='live')
        self.message_user(request, f'{updated} conferences marked as live.')
    mark_as_live.short_description = "Mark selected conferences as live"

    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f'{updated} conferences marked as completed.')
    mark_as_completed.short_description = "Mark selected conferences as completed"

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<int:conference_id>/approve/', self.admin_site.admin_view(self.approve_view), name='conference-approve'),
        ]
        return custom_urls + urls

    def approve_view(self, request, conference_id):
        conference = Conference.objects.get(id=conference_id)
        if not conference.is_approved:
            conference.is_approved = True
            conference.save()
            # Send approval email to chair and organiser
            recipients = []
            if conference.chair.email and '@' in conference.chair.email:
                recipients.append(conference.chair.email)
            if hasattr(conference, 'contact_email') and conference.contact_email and '@' in conference.contact_email:
                recipients.append(conference.contact_email)
            if recipients:
                conference_url = request.build_absolute_uri(reverse('dashboard:conference_submissions', args=[conference.id]))
                send_mail(
                    'Conference Approved',
                    f'Your conference "{conference.name}" has been approved! Manage it here: {conference_url}',
                    'admin@example.com',
                    recipients,
                )
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect('/admin/conference/conference/')

    def approve_selected_conferences(self, request, queryset):
        for conference in queryset:
            if not conference.is_approved:
                conference.is_approved = True
                conference.save()
                recipients = []
                if conference.chair.email and '@' in conference.chair.email:
                    recipients.append(conference.chair.email)
                if hasattr(conference, 'contact_email') and conference.contact_email and '@' in conference.contact_email:
                    recipients.append(conference.contact_email)
                if recipients:
                    from django.urls import reverse
                    conference_url = request.build_absolute_uri(reverse('dashboard:conference_submissions', args=[conference.id]))
                    send_mail(
                        'Conference Approved',
                        f'Your conference "{conference.name}" has been approved! Manage it here: {conference_url}',
                        'admin@example.com',
                        recipients,
                    )
        self.message_user(request, "Selected conferences have been approved and emails sent.")
    approve_selected_conferences.short_description = "Approve selected conferences"

admin.site.register(Conference, ConferenceAdmin)
admin.site.register(ReviewerPool)
admin.site.register(ReviewInvite)
admin.site.register(UserConferenceRole)
admin.site.register(Paper)
admin.site.register(Review)
admin.site.register(Track) 