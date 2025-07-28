from django.contrib import admin
from .models import Conference, ReviewerPool, ReviewInvite, UserConferenceRole, Paper, Review, Track
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.html import format_html

class ConferenceAdmin(admin.ModelAdmin):
    list_display = ('name', 'acronym', 'chair', 'is_approved', 'status', 'start_date', 'end_date', 'approve_conference')
    list_filter = ('is_approved', 'status', 'primary_area', 'start_date')
    search_fields = ('name', 'acronym', 'chair__username', 'chair__email', 'theme_domain')
    list_per_page = 25
    date_hierarchy = 'start_date'
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'acronym', 'description', 'theme_domain')
        }),
        ('Dates & Venue', {
            'fields': ('start_date', 'end_date', 'venue', 'city', 'country')
        }),
        ('Organization', {
            'fields': ('chair', 'chair_name', 'chair_email', 'organizer', 'organizer_web_page')
        }),
        ('Settings', {
            'fields': ('is_approved', 'status', 'primary_area', 'secondary_area', 'area_notes')
        }),
        ('Submission Settings', {
            'fields': ('paper_submission_deadline', 'paper_format', 'abstract_required', 'max_paper_length')
        }),
        ('Contact Information', {
            'fields': ('contact_email', 'contact_phone', 'web_page')
        }),
    )

    def approve_conference(self, obj):
        if not obj.is_approved:
            return format_html('<a class="button" href="/admin/conference/conference/{}/approve/">Approve</a>', obj.id)
        return format_html('<span style="color: green;">✓ Approved</span>')
    approve_conference.short_description = 'Approve Conference'
    approve_conference.allow_tags = True

    actions = ['approve_selected_conferences']

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