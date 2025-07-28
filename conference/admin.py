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
    list_display = ('name', 'acronym', 'chair', 'is_approved', 'status', 'start_date', 'end_date', 'approve_conference', 'conference_actions')
    list_filter = (ConferenceStatusFilter, 'primary_area', 'start_date', 'is_approved')
    search_fields = ('name', 'acronym', 'chair__username', 'chair__email', 'theme_domain', 'venue', 'city')
    list_per_page = 25
    date_hierarchy = 'start_date'
    readonly_fields = ('created_at', 'conference_stats')
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
        actions.append(f'<a href="/admin/conference/paper/?conference__id__exact={obj.id}" style="color: #007bff; text-decoration: none;">📄 Papers</a>')
        actions.append(f'<a href="/admin/conference/userconferencerole/?conference__id__exact={obj.id}" style="color: #007bff; text-decoration: none;">👥 Roles</a>')
        actions.append(f'<a href="/dashboard/conference_submissions/{obj.id}/" style="color: #28a745; text-decoration: none;">🔧 Manage</a>')
        return mark_safe(' | '.join(actions))
    conference_actions.short_description = 'Actions'

    def conference_stats(self, obj):
        if not obj.pk:
            return "Save the conference first to see statistics"
        
        paper_count = obj.papers.count()
        user_count = obj.userconferencerole_set.count()
        review_count = Review.objects.filter(paper__conference=obj).count()
        
        return format_html(
            '<div style="background: #f8f9fa; padding: 10px; border-radius: 5px;">'
            '<h4>Conference Statistics</h4>'
            '<p><strong>Papers:</strong> {}</p>'
            '<p><strong>Users:</strong> {}</p>'
            '<p><strong>Reviews:</strong> {}</p>'
            '</div>',
            paper_count, user_count, review_count
        )
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