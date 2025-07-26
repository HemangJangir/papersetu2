from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from conference.models import Conference, ReviewerPool, ReviewInvite, UserConferenceRole, Paper, Review, User, Notification, PCInvite, ConferenceAdminSettings, EmailTemplate, RegistrationApplication, SubreviewerInvite, Author
from django.db.models import Count, Q
from django.views.decorators.http import require_POST
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from conference.forms import (
    ConferenceInfoForm, SubmissionSettingsForm, ReviewingSettingsForm,
    RebuttalSettingsForm, DecisionSettingsForm, EmailTemplateForm,
    RegistrationApplicationStepOneForm, RegistrationApplicationStepTwoForm
)
from django.views.generic.edit import FormView, CreateView
from django.contrib.auth.decorators import user_passes_test
from django.utils.decorators import method_decorator
from django.core.files.storage import default_storage
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
import os
from django import forms
from django.db import models
from django.utils.html import strip_tags
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse_lazy
from conference.models import Conference
from conference.forms import ConferenceForm
import zipfile
from django.utils.text import slugify
from io import BytesIO
from .models import PCEmailLog
from conference.models import ConferenceFeatureToggle, FEATURE_CHOICES
from openpyxl import Workbook
from django.utils.encoding import smart_str

class PCSendEmailForm(forms.Form):
    RECIPIENT_TYPE_CHOICES = [
        ('pc', 'PC Members'),
        ('author', 'Authors'),
        ('subreviewer', 'Subreviewers'),
    ]
    recipient_type = forms.ChoiceField(choices=RECIPIENT_TYPE_CHOICES, widget=forms.RadioSelect(attrs={'class': 'recipient-type-radio'}), required=True)
    recipients = forms.MultipleChoiceField(choices=[], widget=forms.CheckboxSelectMultiple, required=False)
    subject = forms.CharField(max_length=200, widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded', 'id': 'id_subject'}))
    body = forms.CharField(widget=forms.Textarea(attrs={'class': 'w-full px-4 py-2 border rounded', 'rows': 8, 'id': 'id_body'}))
    attachment = forms.FileField(required=False)
    template = forms.ChoiceField(choices=[], required=False, widget=forms.Select(attrs={'id': 'id_template'}))
    send_test = forms.BooleanField(required=False, label='Send test email to yourself')

    def __init__(self, *args, **kwargs):
        conference = kwargs.pop('conference', None)
        recipient_type = None
        if 'data' in kwargs and kwargs['data']:
            recipient_type = kwargs['data'].get('recipient_type', 'pc')
        super().__init__(*args, **kwargs)
        # Dynamically populate recipients based on recipient_type and conference
        if conference:
            self.fields['recipients'].choices = self.get_recipient_choices(conference, recipient_type or 'pc')
            # Populate template choices if templates exist
            self.fields['template'].choices = self.get_template_choices(conference)

    def get_recipient_choices(self, conference, recipient_type):
        if recipient_type == 'author':
            users = User.objects.filter(userconferencerole__conference=conference, userconferencerole__role='author')
        elif recipient_type == 'subreviewer':
            users = User.objects.filter(userconferencerole__conference=conference, userconferencerole__role='subreviewer')
        else:
            users = User.objects.filter(userconferencerole__conference=conference, userconferencerole__role='pc_member')
        return [(u.id, f"{u.get_full_name() or u.username} ({u.email})") for u in users]

    def get_template_choices(self, conference):
        templates = EmailTemplate.objects.filter(conference=conference)
        return [('', '--- Select Template ---')] + [(t.id, t.subject) for t in templates]

def render_placeholders(text, user=None, paper=None, conference=None, extra=None):
    # Replace placeholders in the text
    context = {
        'name': user.get_full_name() if user else '',
        'submission_title': paper.title if paper else '',
        'deadline': conference.paper_submission_deadline if conference else '',
        'review_link': extra.get('review_link') if extra else '',
        # Add more as needed
    }
    for key, value in context.items():
        text = text.replace(f'{{{{{key}}}}}', str(value))
    return text

@login_required
def dashboard(request):
    user = request.user
    # Determine roles
    roles = UserConferenceRole.objects.filter(user=user).values_list('role', flat=True).distinct()
    is_chair = 'chair' in roles
    is_author = 'author' in roles
    # Chair context
    chaired_confs = Conference.objects.filter(chair=user, is_approved=True)
    if is_chair and chaired_confs.exists():
        # Redirect to the configuration page of the first chaired conference
        first_conf = chaired_confs.first()
        return redirect('dashboard:conference_configuration', conf_id=first_conf.id)
    
    # Check if user is a reviewer (has reviewer profile or pending invitations)
    has_reviewer_profile = hasattr(user, 'reviewer_profile')
    has_pending_invites = ReviewInvite.objects.filter(reviewer=user, status='pending').exists()
    has_accepted_invites = ReviewInvite.objects.filter(reviewer=user, status='accepted').exists()
    is_reviewer = 'reviewer' in roles or has_reviewer_profile or has_pending_invites or has_accepted_invites

    # Get notifications
    notifications = Notification.objects.filter(recipient=user, is_read=False)[:10]

    # Author context
    search_query = request.GET.get('search', '')
    live_upcoming_confs = Conference.objects.filter(status__in=['live', 'upcoming'], is_approved=True)
    if search_query:
        live_upcoming_confs = live_upcoming_confs.filter(
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
        )
    joined_confs = Conference.objects.filter(userconferencerole__user=user, userconferencerole__role='author', is_approved=True)
    submitted_papers = Paper.objects.filter(author=user)

    # Reviewer context
    reviewer_invites = ReviewInvite.objects.filter(reviewer=user, status='pending')
    reviewing_confs = Conference.objects.filter(review_invites__reviewer=user, review_invites__status='accepted').distinct()
    
    # Get papers specifically assigned to this reviewer (papers with Review objects created for this reviewer)
    assigned_papers = Paper.objects.filter(reviews__reviewer=user)
    reviewer_notifications = reviewer_invites
    
    # Get papers that have been assigned to this reviewer but haven't been reviewed yet
    assigned_paper_ids = []
    for conf in reviewing_confs:
        # Get papers in this conference that have been assigned to this reviewer
        conf_papers = conf.papers.filter(reviews__reviewer=user)
        for paper in conf_papers:
            # Check if reviewer has already submitted a review for this paper
            if not Review.objects.filter(paper=paper, reviewer=user, decision__in=['accept', 'reject']).exists():
                assigned_paper_ids.append(paper.id)
    
    pending_paper_reviews = Paper.objects.filter(id__in=assigned_paper_ids)
    
    # Get review statistics for each paper
    paper_review_stats = {}
    for paper in pending_paper_reviews:
        total_reviews = paper.reviews.filter(decision__in=['accept', 'reject']).count()
        accept_count = paper.reviews.filter(decision='accept').count()
        reject_count = paper.reviews.filter(decision='reject').count()
        paper_review_stats[paper.id] = {
            'total_reviews': total_reviews,
            'accept_count': accept_count,
            'reject_count': reject_count,
            'needs_more_reviews': total_reviews < 2,
            'can_be_accepted': accept_count >= 2,
            'can_be_rejected': reject_count > accept_count and total_reviews >= 2
        }

    # All reviewers for modal assignment
    all_reviewers = User.objects.filter(reviewer_profile__isnull=False)

    # For dashboard toggle UI
    dashboard_view = request.GET.get('view', 'chair' if is_chair else 'author' if is_author else 'reviewer')
    
    # Handle success messages
    success_message = request.GET.get('message', '')

    # Get review statistics for all papers
    all_papers_review_stats = {}
    for paper in Paper.objects.all():
        total_reviews = paper.reviews.filter(decision__in=['accept', 'reject']).count()
        accept_count = paper.reviews.filter(decision='accept').count()
        reject_count = paper.reviews.filter(decision='reject').count()
        all_papers_review_stats[paper.id] = {
            'total_reviews': total_reviews,
            'accept_count': accept_count,
            'reject_count': reject_count,
        }

    if is_chair:
        all_chaired_papers = Paper.objects.filter(conference__in=chaired_confs)
    else:
        all_chaired_papers = Paper.objects.none()

    context = {
        'roles': roles,
        'dashboard_view': dashboard_view,
        'is_chair': is_chair,
        'is_author': is_author,
        'is_reviewer': is_reviewer,
        'chaired_confs': chaired_confs,
        'joined_confs': joined_confs,
        'submitted_papers': submitted_papers,
        'reviewing_confs': reviewing_confs,
        'assigned_papers': assigned_papers,
        'reviewer_invites': reviewer_invites,
        'live_upcoming_confs': live_upcoming_confs,
        'search_query': search_query,
        'pending_paper_reviews': pending_paper_reviews,
        'all_reviewers': all_reviewers,
        'notifications': notifications,
        'success_message': success_message,
        'paper_review_stats': paper_review_stats,
        'all_papers_review_stats': all_papers_review_stats,
        'all_chaired_papers': all_chaired_papers,
    }
    # Add nav bar context for dashboard
    nav_items = [
        "Submissions", "Reviews", "Status", "PC", "Events",
        "Email", "Administration", "Conference", "News", "papersetu"
    ]
    active_tab = "Submissions"
    # If user has at least one conference, use the first for dropdowns
    conference = chaired_confs.first() or joined_confs.first() or reviewing_confs.first()
    review_dropdown_items = []
    if conference:
        review_dropdown_items = [
            {'label': 'All submissions', 'url': reverse('dashboard:all_submissions', args=[conference.id])},
            {'label': 'Assigned to me', 'url': reverse('dashboard:assigned_to_me', args=[conference.id])},
            {'label': 'Subreviewers', 'url': reverse('dashboard:subreviewers', args=[conference.id])},
            {'label': 'Pool of subreviewers', 'url': reverse('dashboard:pool_subreviewers', args=[conference.id])},
            {'label': 'By PC member', 'url': reverse('dashboard:by_pc_member', args=[conference.id])},
            {'label': 'By submission', 'url': reverse('dashboard:by_submission', args=[conference.id])},
            {'label': 'Delete', 'url': reverse('dashboard:delete_review', args=[conference.id])},
            {'label': 'Send to authors', 'url': reverse('dashboard:send_to_authors', args=[conference.id])},
            {'label': 'Missing reviews', 'url': reverse('dashboard:missing_reviews', args=[conference.id])},
        ]
    context.update({
        'nav_items': nav_items,
        'active_tab': active_tab,
        'review_dropdown_items': review_dropdown_items,
        'conference': conference,
    })
    return render(request, 'dashboard/dashboard.html', context)

@require_POST
@login_required
def review_invite_respond(request, invite_id):
    invite = get_object_or_404(ReviewInvite, id=invite_id, reviewer=request.user)
    response = request.POST.get('response')
    if response == 'accept':
        invite.status = 'accepted'
        invite.save()
        UserConferenceRole.objects.get_or_create(user=request.user, conference=invite.conference, role='reviewer')
        
        # Create notification for chair
        Notification.objects.create(
            recipient=invite.conference.chair,
            notification_type='reviewer_response',
            title=f'Reviewer Accepted Invitation',
            message=f'{request.user.get_full_name()} ({request.user.username}) has accepted the reviewer invitation for {invite.conference.name}.',
            related_conference=invite.conference,
            related_review_invite=invite
        )
        
    elif response == 'decline':
        invite.status = 'declined'
        invite.save()
        
        # Create notification for chair
        Notification.objects.create(
            recipient=invite.conference.chair,
            notification_type='reviewer_response',
            title=f'Reviewer Declined Invitation',
            message=f'{request.user.get_full_name()} ({request.user.username}) has declined the reviewer invitation for {invite.conference.name}.',
            related_conference=invite.conference,
            related_review_invite=invite
        )
    
    return HttpResponseRedirect(reverse('dashboard:dashboard') + '?view=reviewer')

@login_required
def review_paper(request, paper_id):
    review = get_object_or_404(Review, id=paper_id, reviewer=request.user)
    conference = review.paper.conference
    nav_items = [
        "Submissions", "Reviews", "Status", "PC", "Events",
        "Email", "Administration", "Conference", "News", "papersetu"
    ]
    active_tab = "Reviews"
    review_dropdown_items = [
        {'label': 'All submissions', 'url': reverse('dashboard:all_submissions', args=[conference.id])},
        {'label': 'Assigned to me', 'url': reverse('dashboard:assigned_to_me', args=[conference.id])},
        {'label': 'Subreviewers', 'url': reverse('dashboard:subreviewers', args=[conference.id])},
        {'label': 'Pool of subreviewers', 'url': reverse('dashboard:pool_subreviewers', args=[conference.id])},
        {'label': 'By PC member', 'url': reverse('dashboard:by_pc_member', args=[conference.id])},
        {'label': 'By submission', 'url': reverse('dashboard:by_submission', args=[conference.id])},
        {'label': 'Delete', 'url': reverse('dashboard:delete_review', args=[conference.id])},
        {'label': 'Send to authors', 'url': reverse('dashboard:send_to_authors', args=[conference.id])},
        {'label': 'Missing reviews', 'url': reverse('dashboard:missing_reviews', args=[conference.id])},
    ]
    context = {
        'review': review,
        'conference': conference,
        'nav_items': nav_items,
        'active_tab': active_tab,
        'review_dropdown_items': review_dropdown_items,
    }
    return render(request, 'dashboard/review_paper.html', context)

@require_POST
@login_required
def paper_review_respond(request, review_id):
    review = get_object_or_404(Review, id=review_id, reviewer=request.user, decision__isnull=True)
    response = request.POST.get('response')
    if response == 'accept':
        # Reviewer accepts assignment, do nothing (keep Review object)
        pass
    elif response == 'decline':
        # Reviewer declines assignment, delete Review object
        review.delete()
    return HttpResponseRedirect(reverse('dashboard:dashboard') + '?view=reviewer')

@login_required
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notification.is_read = True
    notification.save()
    return JsonResponse({'status': 'success'})

@require_POST
@login_required
def bulk_assign_papers(request):
    user = request.user
    # Check if user is a chair
    chaired_confs = Conference.objects.filter(chair=user)
    if not chaired_confs.exists():
        messages.error(request, 'You are not authorized to assign papers.')
        return redirect('dashboard:dashboard')
    
    paper_ids = request.POST.getlist('papers')
    reviewer_ids = request.POST.getlist('reviewers')
    
    if not paper_ids or not reviewer_ids:
        messages.error(request, 'Please select at least one paper and one reviewer.')
        return redirect('dashboard:dashboard')
    
    papers = Paper.objects.filter(id__in=paper_ids, conference__chair=user)
    reviewers = User.objects.filter(id__in=reviewer_ids)
    
    assigned_count = 0
    errors = []
    
    for paper in papers:
        for reviewer in reviewers:
            # Check if reviewer is accepted for this specific conference
            try:
                invite = ReviewInvite.objects.get(conference=paper.conference, reviewer=reviewer)
                if invite.status == 'accepted':
                    # Create Review object to assign the paper to reviewer
                    review, review_created = Review.objects.get_or_create(
                        paper=paper,
                        reviewer=reviewer,
                        defaults={'decision': None}  # None means not reviewed yet
                    )
                    
                    if review_created:
                        assigned_count += 1
                        # Notify reviewer
                        Notification.objects.create(
                            recipient=reviewer,
                            notification_type='paper_assignment',
                            title=f'Paper Assignment',
                            message=f'You have been assigned to review the paper "{paper.title}" for {paper.conference.name}.',
                            related_paper=paper,
                            related_conference=paper.conference
                        )
                    else:
                        errors.append(f"{reviewer.username} was already assigned to paper '{paper.title}'")
                else:
                    errors.append(f"{reviewer.username} has not accepted the invitation for {paper.conference.name}")
            except ReviewInvite.DoesNotExist:
                errors.append(f"{reviewer.username} has not been invited to {paper.conference.name}")
    
    if assigned_count > 0:
        messages.success(request, f'Successfully assigned {assigned_count} paper-reviewer pairs!')
    if errors:
        messages.warning(request, f'Some assignments failed: {", ".join(errors[:3])}{"..." if len(errors) > 3 else ""}')
    
    return redirect('dashboard:dashboard')

@login_required
def pc_conference_detail(request, conf_id):
    conference = get_object_or_404(Conference, id=conf_id)
    user = request.user
    # Check if user is a pc_member for this conference
    is_pc_member = UserConferenceRole.objects.filter(user=user, conference=conference, role='pc_member').exists()
    if not is_pc_member:
        return render(request, 'dashboard/forbidden.html', {'message': 'You are not a PC member for this conference.'})
    # Get submissions and reviews for this conference
    submissions = Paper.objects.filter(conference=conference).select_related('author')
    for paper in submissions:
        paper.can_review = paper.reviews.filter(reviewer=user).exists()
        paper.review_id = paper.reviews.filter(reviewer=user).first().id if paper.can_review else None
    reviews = Review.objects.filter(paper__conference=conference)
    nav_items = [
        {'label': 'Submissions', 'url': '#'},
        {'label': 'Reviews', 'url': '#'},
        {'label': 'Status', 'url': '#'},
        {'label': 'Events', 'url': '#'},
        {'label': 'Conference', 'url': '#'},
        {'label': 'News', 'url': '#'},
    ]
    context = {
        'conference': conference,
        'submissions': submissions,
        'reviews': reviews,
        'nav_items': nav_items,
    }
    return render(request, 'dashboard/pc_conference_detail.html', context)

@login_required
def pc_list(request, conf_id):
    conference = get_object_or_404(Conference, id=conf_id)
    if not (conference.chair == request.user or UserConferenceRole.objects.filter(user=request.user, conference=conference, role='pc_member').exists()):
        return render(request, 'dashboard/forbidden.html', {'message': 'You do not have permission.'})
    pc_members = UserConferenceRole.objects.filter(conference=conference, role='pc_member').select_related('user')
    context = {'conference': conference, 'pc_members': pc_members}
    return render(request, 'dashboard/pc_list.html', context)

@login_required
def pc_invite(request, conf_id):
    conference = get_object_or_404(Conference, id=conf_id)
    if conference.chair != request.user:
        return render(request, 'dashboard/forbidden.html', {'message': 'Only the chair can invite PC members.'})
    
    message = ''
    message_type = 'success'
    mail_preview = None
    
    # Get all users except chair, already-invited, and current PC members
    User = get_user_model()
    invited_emails = set(PCInvite.objects.filter(conference=conference, status='pending').values_list('email', flat=True))
    pc_member_emails = set(UserConferenceRole.objects.filter(conference=conference, role='pc_member').values_list('user__email', flat=True))
    all_users = User.objects.exclude(id=conference.chair_id).exclude(email__in=invited_emails | pc_member_emails)
    
    if request.method == 'POST':
        # Handle single invitation
        if 'name' in request.POST and 'email' in request.POST:
            name = request.POST.get('name').strip()
            email = request.POST.get('email').strip()
            
            if not name or not email:
                message = 'Name and email are required.'
                message_type = 'error'
            else:
                # Check if already invited or PC member
                if email in invited_emails:
                    message = f'{email} has already been invited.'
                    message_type = 'error'
                elif email in pc_member_emails:
                    message = f'{email} is already a PC member.'
                    message_type = 'error'
                else:
                    # Create invitation
                    token = get_random_string(48)
                    invite = PCInvite.objects.create(
                        conference=conference,
                        name=name,
                        email=email,
                        invited_by=request.user,
                        token=token
                    )
                    
                    # Send email
                    subject = f"PC Invitation for {conference.name}"
                    body = f"""Dear {name},

You have been invited to serve as a Program Committee (PC) member for the conference "{conference.name}".

Please click the following link to accept or decline this invitation:
{request.build_absolute_uri(reverse('dashboard:pc_invite_accept', args=[token]))}

Best regards,
{request.user.get_full_name() or request.user.username}
Conference Chair"""
                    
                    # Use DEFAULT_FROM_EMAIL or fallback to EMAIL_HOST_USER
                    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER)
                    
                    try:
                        # Try using EmailMessage first
                        from django.core.mail import EmailMessage
                        email_msg = EmailMessage(
                            subject=subject,
                            body=body,
                            from_email=from_email,
                            to=[email],
                        )
                        email_msg.send(fail_silently=False)
                        message = f'Invitation sent successfully to {name} ({email}).'
                        message_type = 'success'
                        # Log the invitation email
                        PCEmailLog.objects.create(
                            subject=subject,
                            body=body,
                            recipients=email,
                            conference=conference,
                            sender=request.user,
                            attachment_name='',
                        )
                    except Exception as e:
                        error_msg = str(e)
                        if 'SSL' in error_msg or 'CERTIFICATE' in error_msg:
                            # Try alternative approach for SSL issues
                            try:
                                import smtplib
                                from email.mime.text import MIMEText
                                from email.mime.multipart import MIMEMultipart
                                
                                msg = MIMEMultipart()
                                msg['From'] = from_email
                                msg['To'] = email
                                msg['Subject'] = subject
                                msg.attach(MIMEText(body, 'plain'))
                                
                                server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
                                server.starttls()
                                server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
                                server.send_message(msg)
                                server.quit()
                                
                                message = f'Invitation sent successfully to {name} ({email}).'
                                message_type = 'success'
                            except Exception as ssl_error:
                                message = f'SSL Certificate error: {ssl_error}. Please check email configuration or use console backend for development.'
                                message_type = 'error'
                                invite.delete()
                        elif 'DEFAULT_FROM_EMAIL' in error_msg:
                            message = f'Email configuration error: Please check DEFAULT_FROM_EMAIL setting.'
                            message_type = 'error'
                            invite.delete()
                        elif 'SMTP' in error_msg or 'authentication' in error_msg.lower():
                            message = f'Email server error: Please check email credentials and SMTP settings.'
                            message_type = 'error'
                            invite.delete()
                        else:
                            message = f'Failed to send email to {email}: {error_msg}'
                            message_type = 'error'
                            invite.delete()
        
        # Handle bulk invitations
        elif 'bulk_invite' in request.POST:
            bulk_text = request.POST.get('bulk_invite').strip()
            if not bulk_text:
                message = 'Please provide users to invite.'
                message_type = 'error'
            else:
                lines = [line.strip() for line in bulk_text.split('\n') if line.strip()]
                success_count = 0
                error_count = 0
                error_messages = []
                
                for line in lines:
                    parts = [part.strip() for part in line.split(',')]
                    if len(parts) >= 2:
                        name = parts[0]
                        email = parts[1]
                        
                        # Validate email format
                        if '@' not in email:
                            error_messages.append(f'Invalid email format for {name}: {email}')
                            error_count += 1
                            continue
                        
                        # Check if already invited or PC member
                        if email in invited_emails:
                            error_messages.append(f'{email} has already been invited.')
                            error_count += 1
                            continue
                        elif email in pc_member_emails:
                            error_messages.append(f'{email} is already a PC member.')
                            error_count += 1
                            continue
                        
                        # Create invitation
                        token = get_random_string(48)
                        invite = PCInvite.objects.create(
                            conference=conference,
                            name=name,
                            email=email,
                            invited_by=request.user,
                            token=token
                        )
                        
                        # Send email
                        subject = f"PC Invitation for {conference.name}"
                        body = f"""Dear {name},

You have been invited to serve as a Program Committee (PC) member for the conference "{conference.name}".

Please click the following link to accept or decline this invitation:
{request.build_absolute_uri(reverse('dashboard:pc_invite_accept', args=[token]))}

Best regards,
{request.user.get_full_name() or request.user.username}
Conference Chair"""
                        
                        try:
                            # Try using EmailMessage first
                            from django.core.mail import EmailMessage
                            email_msg = EmailMessage(
                                subject=subject,
                                body=body,
                                from_email=settings.DEFAULT_FROM_EMAIL,
                                to=[email],
                            )
                            email_msg.send(fail_silently=False)
                            success_count += 1
                            # Log the invitation email
                            PCEmailLog.objects.create(
                                subject=subject,
                                body=body,
                                recipients=email,
                                conference=conference,
                                sender=request.user,
                                attachment_name='',
                            )
                        except Exception as e:
                            error_msg = str(e)
                            if 'SSL' in error_msg or 'CERTIFICATE' in error_msg:
                                # Try alternative approach for SSL issues
                                try:
                                    import smtplib
                                    from email.mime.text import MIMEText
                                    from email.mime.multipart import MIMEMultipart
                                    
                                    msg = MIMEMultipart()
                                    msg['From'] = settings.DEFAULT_FROM_EMAIL
                                    msg['To'] = email
                                    msg['Subject'] = subject
                                    msg.attach(MIMEText(body, 'plain'))
                                    
                                    server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
                                    server.starttls()
                                    server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
                                    server.send_message(msg)
                                    server.quit()
                                    
                                    success_count += 1
                                    # Log the invitation email
                                    PCEmailLog.objects.create(
                                        subject=subject,
                                        body=body,
                                        recipients=email,
                                        conference=conference,
                                        sender=request.user,
                                        attachment_name='',
                                    )
                                except Exception as ssl_error:
                                    error_messages.append(f'SSL Certificate error for {email}: {ssl_error}. Please check email configuration or use console backend for development.')
                                    error_count += 1
                                    invite.delete()
                            elif 'DEFAULT_FROM_EMAIL' in error_msg:
                                error_messages.append(f'Email configuration error for {email}: Please check DEFAULT_FROM_EMAIL setting.')
                                error_count += 1
                                invite.delete()
                            elif 'SMTP' in error_msg or 'authentication' in error_msg.lower():
                                error_messages.append(f'Email server error for {email}: Please check email credentials and SMTP settings.')
                                error_count += 1
                                invite.delete()
                            else:
                                error_messages.append(f'Failed to send email to {email}: {error_msg}')
                                error_count += 1
                                invite.delete()
                    else:
                        error_messages.append(f'Invalid format: {line} (expected: Name, Email)')
                        error_count += 1
                
                # Prepare summary message
                if success_count > 0 and error_count == 0:
                    message = f'Successfully sent {success_count} invitation(s).'
                    message_type = 'success'
                elif success_count > 0 and error_count > 0:
                    message = f'Successfully sent {success_count} invitation(s). {error_count} failed.'
                    message_type = 'warning'
                else:
                    message = f'Failed to send any invitations. {error_count} error(s).'
                    message_type = 'error'
                
                # Add error details if any
                if error_messages:
                    message += '\n\nErrors:\n' + '\n'.join(error_messages[:5])  # Show first 5 errors
                    if len(error_messages) > 5:
                        message += f'\n... and {len(error_messages) - 5} more errors.'
    
    # Get all invites for display
    invites = PCInvite.objects.filter(conference=conference).order_by('-sent_at')
    
    # Update the user list to exclude newly invited users
    invited_emails = set(PCInvite.objects.filter(conference=conference, status='pending').values_list('email', flat=True))
    pc_member_emails = set(UserConferenceRole.objects.filter(conference=conference, role='pc_member').values_list('user__email', flat=True))
    all_users = User.objects.exclude(id=conference.chair_id).exclude(email__in=invited_emails | pc_member_emails)
    
    context = {
        'conference': conference, 
        'message': message, 
        'message_type': message_type,
        'mail_preview': mail_preview, 
        'invites': invites, 
        'all_users': all_users
    }
    return render(request, 'dashboard/pc_invite.html', context)

def pc_invite_accept(request, token):
    invite = get_object_or_404(PCInvite, token=token)
    if invite.status != 'pending':
        return render(request, 'dashboard/pc_invite_responded.html', {'invite': invite})
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'accept':
            # Create user if not exists
            User = get_user_model()
            user, created = User.objects.get_or_create(email=invite.email, defaults={'username': invite.email.split('@')[0], 'first_name': invite.name})
            UserConferenceRole.objects.get_or_create(user=user, conference=invite.conference, role='pc_member')
            invite.status = 'accepted'
            invite.accepted_at = timezone.now()
            invite.save()
            # Notify chair
            send_mail(
                f"PC Invitation Accepted for {invite.conference.name}",
                f"{invite.name} ({invite.email}) has accepted your PC invitation for {invite.conference.name}.",
                settings.DEFAULT_FROM_EMAIL,
                [invite.invited_by.email]
            )
            return render(request, 'dashboard/pc_invite_responded.html', {'invite': invite, 'accepted': True})
        elif action == 'decline':
            invite.status = 'declined'
            invite.save()
            return render(request, 'dashboard/pc_invite_responded.html', {'invite': invite, 'declined': True})
    context = {'invite': invite}
    return render(request, 'dashboard/pc_invite_accept.html', context)

@login_required
def pc_invitations(request, conf_id):
    conference = get_object_or_404(Conference, id=conf_id)
    if conference.chair != request.user:
        return render(request, 'dashboard/forbidden.html', {'message': 'Only the chair can view invitations.'})
    invitations = PCInvite.objects.filter(conference=conference, status='pending')
    context = {'conference': conference, 'invitations': invitations}
    return render(request, 'dashboard/pc_invitations.html', context)

@login_required
def pc_remove(request, conf_id, user_id):
    conference = get_object_or_404(Conference, id=conf_id)
    if conference.chair != request.user:
        return render(request, 'dashboard/forbidden.html', {'message': 'Only the chair can remove PC members.'})
    UserConferenceRole.objects.filter(conference=conference, user_id=user_id, role='pc_member').delete()
    return redirect('dashboard:pc_list', conf_id=conf_id)

@login_required
def conference_submissions(request, conf_id):
    """
    Display all paper submissions for a specific conference.
    Accessible by conference chair and PC members.
    """
    conference = get_object_or_404(Conference, id=conf_id)
    user = request.user
    
    # Check if user has permission to view submissions (chair or PC member)
    is_chair = conference.chair == user
    is_pc_member = UserConferenceRole.objects.filter(
        user=user, 
        conference=conference, 
        role='pc_member'
    ).exists()
    
    if not (is_chair or is_pc_member):
        return render(request, 'dashboard/forbidden.html', {
            'message': 'You do not have permission to view submissions for this conference.'
        })
    
    # Get all papers submitted to this conference
    papers = Paper.objects.filter(conference=conference).select_related('author').order_by('-submitted_at')
    
    # Filter by status if requested
    status_filter = request.GET.get('status', 'all')
    if status_filter != 'all':
        papers = papers.filter(status=status_filter)
    # Re-calculate review statistics for filtered papers
    for paper in papers:
        reviews = paper.reviews.all()
        paper.total_reviews = reviews.count()
        paper.reviews_with_decision = reviews.filter(decision__in=['accept', 'reject']).count()
        paper.accept_count = reviews.filter(decision='accept').count()
        paper.reject_count = reviews.filter(decision='reject').count()
        paper.pending_reviews = paper.total_reviews - paper.reviews_with_decision
        paper.assigned_reviewers = [
            {
                'user': review.reviewer,
                'decision': review.decision,
                'submitted_at': review.submitted_at
            }
            for review in reviews
        ]
        paper.latest_subreviewer_recommendation = reviews.filter(recommendation__isnull=False, decision__isnull=True).order_by('-submitted_at').first()
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        papers = papers.filter(
            Q(title__icontains=search_query) |
            Q(author__first_name__icontains=search_query) |
            Q(author__last_name__icontains=search_query) |
            Q(author__username__icontains=search_query) |
            Q(abstract__icontains=search_query) |
            Q(paper_id__icontains=search_query)
        )
    
    # Navigation items for the conference
    nav_items = [
        "Submissions", "Reviews", "Status", "PC", "Events",
        "Email", "Administration", "Conference", "News", "papersetu"
    ]
    
    # Statistics
    total_submissions = Paper.objects.filter(conference=conference).count()
    accepted_papers = Paper.objects.filter(conference=conference, status='accepted').count()
    rejected_papers = Paper.objects.filter(conference=conference, status='rejected').count()
    pending_papers = Paper.objects.filter(conference=conference, status='submitted').count()
    
    context = {
        'conference': conference,
        'papers': papers,
        'is_chair': is_chair,
        'is_pc_member': is_pc_member,
        'nav_items': nav_items,
        'active_tab': 'Submissions',
        'status_filter': status_filter,
        'search_query': search_query,
        'total_submissions': total_submissions,
        'accepted_papers': accepted_papers,
        'rejected_papers': rejected_papers,
        'pending_papers': pending_papers,
    }
    
    return render(request, 'dashboard/conference_submissions.html', context)

@login_required
def conference_details(request, conf_id):
    """
    Display detailed information about a specific conference.
    Accessible by conference chair, PC members, and authors.
    """
    conference = get_object_or_404(Conference, id=conf_id)
    user = request.user
    
    # Check if user has any role in this conference
    user_roles = UserConferenceRole.objects.filter(
        user=user, 
        conference=conference
    ).values_list('role', flat=True)
    
    is_chair = conference.chair == user
    is_pc_member = 'pc_member' in user_roles
    is_author = 'author' in user_roles
    is_reviewer = 'reviewer' in user_roles
    
    if not (is_chair or is_pc_member or is_author or is_reviewer):
        return render(request, 'dashboard/forbidden.html', {
            'message': 'You do not have permission to view details for this conference.'
        })
    
    # Get user's available roles for role switching
    available_roles = []
    if is_chair:
        available_roles.append(('chair', 'Chair'))
    if is_pc_member:
        available_roles.append(('pc_member', 'PC Member'))
    if is_author:
        available_roles.append(('author', 'Author'))
    if is_reviewer:
        available_roles.append(('reviewer', 'Reviewer'))
    
    # Get co-chairs (PC members with special designation)
    co_chairs = UserConferenceRole.objects.filter(
        conference=conference, 
        role='pc_member'
    ).select_related('user').exclude(user=conference.chair)
    
    # Navigation items for the conference
    nav_items = [
        "Submissions", "Reviews", "Status", "PC", "Events",
        "Email", "Administration", "Conference", "News", "papersetu"
    ]
    
    context = {
        'conference': conference,
        'is_chair': is_chair,
        'is_pc_member': is_pc_member,
        'is_author': is_author,
        'is_reviewer': is_reviewer,
        'available_roles': available_roles,
        'co_chairs': co_chairs,
        'nav_items': nav_items,
        'active_tab': 'Conference',
        'today': date.today(),
    }
    
    return render(request, 'dashboard/conference_details.html', context)

@login_required
def conference_administration(request, conf_id):
    """
    Display the administration panel with configuration options.
    Shows a menu-style interface like EasyChair.
    """
    conference = get_object_or_404(Conference, id=conf_id)
    user = request.user
    
    # Ensure only the chair can access the administration panel
    if conference.chair != user:
        return render(request, 'dashboard/forbidden.html', {
            'message': 'Only the conference chair can access the administration panel.'
        })
    
    # Administration menu items (like EasyChair style)
    admin_menu_items = [
        {
            'name': 'Config',
            'description': 'Configure conference settings',
            'url': 'dashboard:conference_configuration',
            'icon': 'fas fa-cog',
            'highlighted': True  # This will be the main highlighted item
        },
        {
            'name': 'Registration',
            'description': 'Manage participant registration',
            'url': 'dashboard:registration_application_step1',
            'icon': 'fas fa-user-plus',
            'highlighted': False
        },
        {
            'name': 'Other utilities',
            'description': 'Additional administrative tools',
            'url': '#',
            'icon': 'fas fa-tools',
            'highlighted': False
        },
        {
            'name': 'Analytics',
            'description': 'Conference analytics and reports',
            'url': '#',
            'icon': 'fas fa-chart-line',
            'highlighted': False
        },
        {
            'name': 'Statistics',
            'description': 'Conference statistics overview',
            'url': '#',
            'icon': 'fas fa-chart-bar',
            'highlighted': False
        },
        {
            'name': 'Demo version',
            'description': 'Demo mode settings',
            'url': '#',
            'icon': 'fas fa-play-circle',
            'highlighted': False
        },
        {
            'name': 'Tracks',
            'description': 'Manage conference tracks',
            'url': '#',
            'icon': 'fas fa-route',
            'highlighted': False
        },
        {
            'name': 'Create CFP',
            'description': 'Create Call for Papers',
            'url': '#',
            'icon': 'fas fa-bullhorn',
            'highlighted': False
        },
        {
            'name': 'Create program',
            'description': 'Create conference program',
            'url': '#',
            'icon': 'fas fa-calendar-alt',
            'highlighted': False
        },
        {
            'name': 'Create proceedings',
            'description': 'Generate proceedings',
            'url': '#',
            'icon': 'fas fa-book',
            'highlighted': False
        },
    ]
    
    # Navigation items for the conference
    nav_items = [
        "Submissions", "Reviews", "Status", "PC", "Events",
        "Email", "Administration", "Conference", "News", "papersetu"
    ]
    
    context = {
        'conference': conference,
        'admin_menu_items': admin_menu_items,
        'nav_items': nav_items,
        'active_tab': 'Administration',
    }
    
    return render(request, 'dashboard/conference_administration.html', context)

@login_required
def conference_configuration(request, conf_id):
    """
    Display and handle the conference configuration panel.
    Allows chairs to view and edit all conference settings.
    """
    conference = get_object_or_404(Conference, id=conf_id)
    user = request.user

    # Ensure only the chair can access the configuration panel
    if conference.chair != user:
        return render(request, 'dashboard/forbidden.html', {
            'message': 'Only the conference chair can access the configuration panel.'
        })

    edit_section = request.GET.get('edit')
    message = None
    forms_data = {}

    # Handle Conference Info edit POST
    if request.method == 'POST' and request.POST.get('section') == 'conference_info':
        form = ConferenceInfoForm(request.POST, instance=conference)
        if form.is_valid():
            form.save()
            messages.success(request, 'Conference information updated successfully.')
            return redirect('dashboard:conference_configuration', conf_id=conf_id)
        else:
            forms_data['conference_info'] = form
            edit_section = 'info'
    else:
        forms_data['conference_info'] = ConferenceInfoForm(instance=conference)

    # Navigation items for the conference
    nav_items = [
        "Submissions", "Reviews", "Status", "PC", "Events",
        "Email", "Administration", "Conference", "News", "papersetu"
    ]

    context = {
        'conference': conference,
        'forms': forms_data,
        'edit_section': edit_section,
        'nav_items': nav_items,
        'active_tab': 'Administration',
    }

    return render(request, 'dashboard/conference_configuration.html', context)

@login_required
def registration_application_step1(request, conf_id):
    """
    First step of registration application wizard.
    """
    conference = get_object_or_404(Conference, id=conf_id)
    user = request.user
    
    # Ensure only the chair can access
    if conference.chair != user:
        return render(request, 'dashboard/forbidden.html', {
            'message': 'Only the conference chair can apply for registration.'
        })
    
    # Check if application already exists
    try:
        existing_app = RegistrationApplication.objects.get(conference=conference)
        if existing_app.status == 'approved':
            messages.info(request, 'Registration has already been approved for this conference.')
            return redirect('dashboard:registration_status', conf_id=conf_id)
        elif existing_app.status == 'pending':
            messages.info(request, 'Your registration application is pending review.')
            return redirect('dashboard:registration_status', conf_id=conf_id)
    except RegistrationApplication.DoesNotExist:
        pass
    
    if request.method == 'POST':
        form = RegistrationApplicationStepOneForm(request.POST)
        if form.is_valid():
            # Store form data in session (convert date to string for JSON serialization)
            cleaned_data = form.cleaned_data.copy()
            if 'registration_start_date' in cleaned_data:
                cleaned_data['registration_start_date'] = cleaned_data['registration_start_date'].isoformat()
            request.session['registration_step1'] = cleaned_data
            return redirect('dashboard:registration_application_step2', conf_id=conf_id)
    else:
        form = RegistrationApplicationStepOneForm()
    
    context = {
        'conference': conference,
        'form': form,
        'step': 1,
        'total_steps': 2,
    }
    return render(request, 'dashboard/registration_application_step1.html', context)

@login_required
def registration_application_step2(request, conf_id):
    """
    Second step of registration application wizard.
    """
    conference = get_object_or_404(Conference, id=conf_id)
    user = request.user
    
    # Ensure only the chair can access
    if conference.chair != user:
        return render(request, 'dashboard/forbidden.html', {
            'message': 'Only the conference chair can apply for registration.'
        })
    
    # Check if step 1 data exists
    if 'registration_step1' not in request.session:
        messages.error(request, 'Please complete step 1 first.')
        return redirect('dashboard:registration_application_step1', conf_id=conf_id)
    
    if request.method == 'POST':
        form = RegistrationApplicationStepTwoForm(request.POST)
        if form.is_valid():
            # Combine data from both steps
            step1_data = request.session['registration_step1']
            step2_data = form.cleaned_data
            
            # Convert date string back to date object
            from datetime import datetime
            registration_start_date = datetime.fromisoformat(step1_data['registration_start_date']).date()
            
            # Create the application
            application = RegistrationApplication.objects.create(
                conference=conference,
                organizer=step1_data['organizer'],
                country_region=step1_data['country_region'],
                registration_start_date=registration_start_date,
                estimated_attendees=step2_data['estimated_attendees'],
                notes=step2_data['notes']
            )
            
            # Clear session data
            if 'registration_step1' in request.session:
                del request.session['registration_step1']
            
            # Send notification email to conference contact
            if conference.contact_email:
                try:
                    send_mail(
                        subject=f'Registration Application Submitted - {conference.name}',
                        message=f'''Dear Conference Chair,

Your registration application for {conference.name} has been submitted successfully.

Application Details:
- Organizer: {application.organizer}
- Country/Region: {application.country_region}
- Registration Start Date: {application.registration_start_date}
- Estimated Attendees: {application.estimated_attendees}

Status: Pending Review

You will be notified once the application is reviewed.

Best regards,
PaperSetu Team''',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[conference.contact_email],
                        fail_silently=True,
                    )
                except Exception as e:
                    print(f"Email send failed: {e}")
            
            messages.success(request, 'Registration application submitted successfully!')
            return redirect('dashboard:registration_confirmation', conf_id=conf_id)
    else:
        form = RegistrationApplicationStepTwoForm()
    
    # Get step 1 data for display
    step1_data = request.session.get('registration_step1', {})
    
    context = {
        'conference': conference,
        'form': form,
        'step1_data': step1_data,
        'step': 2,
        'total_steps': 2,
    }
    return render(request, 'dashboard/registration_application_step2.html', context)

@login_required
def registration_confirmation(request, conf_id):
    """
    Registration application confirmation page.
    """
    conference = get_object_or_404(Conference, id=conf_id)
    user = request.user
    
    # Ensure only the chair can access
    if conference.chair != user:
        return render(request, 'dashboard/forbidden.html', {
            'message': 'Access denied.'
        })
    
    try:
        application = RegistrationApplication.objects.get(conference=conference)
    except RegistrationApplication.DoesNotExist:
        messages.error(request, 'No registration application found.')
        return redirect('dashboard:registration_application_step1', conf_id=conf_id)
    
    context = {
        'conference': conference,
        'application': application,
    }
    return render(request, 'dashboard/registration_confirmation.html', context)

@login_required
def registration_status(request, conf_id):
    """
    Show current registration application status.
    """
    conference = get_object_or_404(Conference, id=conf_id)
    user = request.user
    
    # Ensure only the chair can access
    if conference.chair != user:
        return render(request, 'dashboard/forbidden.html', {
            'message': 'Access denied.'
        })
    
    try:
        application = RegistrationApplication.objects.get(conference=conference)
    except RegistrationApplication.DoesNotExist:
        messages.info(request, 'No registration application found. You can apply now.')
        return redirect('dashboard:registration_application_step1', conf_id=conf_id)
    
    context = {
        'conference': conference,
        'application': application,
    }
    return render(request, 'dashboard/registration_status.html', context)

# Other Utilities Views
@login_required
def other_utilities(request, conf_id):
    """
    Other utilities main page with dropdown options.
    """
    conference = get_object_or_404(Conference, id=conf_id)
    user = request.user
    
    # Ensure only the chair can access
    if conference.chair != user:
        return render(request, 'dashboard/forbidden.html', {
            'message': 'Only the conference chair can access utilities.'
        })
    
    context = {
        'conference': conference,
    }
    return render(request, 'dashboard/other_utilities.html', context)

@login_required
def accepted_submissions_list(request, conf_id):
    """
    Display list of accepted submissions.
    """
    conference = get_object_or_404(Conference, id=conf_id)
    user = request.user
    
    # Ensure only the chair can access
    if conference.chair != user:
        return render(request, 'dashboard/forbidden.html', {
            'message': 'Only the conference chair can access this feature.'
        })
    
    # Get accepted papers
    accepted_papers = Paper.objects.filter(
        conference=conference, 
        status='accepted'
    ).select_related('author').order_by('title')
    
    context = {
        'conference': conference,
        'papers': accepted_papers,
        'total_count': accepted_papers.count(),
    }
    return render(request, 'dashboard/accepted_submissions.html', context)

@login_required
def export_accepted_submissions_csv(request, conf_id):
    """
    Export accepted submissions as CSV.
    """
    import csv
    from django.http import HttpResponse
    
    conference = get_object_or_404(Conference, id=conf_id)
    user = request.user
    
    # Ensure only the chair can access
    if conference.chair != user:
        return render(request, 'dashboard/forbidden.html', {
            'message': 'Only the conference chair can access this feature.'
        })
    
    # Create the HttpResponse object with CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{conference.acronym}_accepted_submissions.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Title', 'Author', 'Email', 'Submitted Date', 'Status'])
    
    # Get accepted papers
    accepted_papers = Paper.objects.filter(
        conference=conference, 
        status='accepted'
    ).select_related('author')
    
    for paper in accepted_papers:
        writer.writerow([
            paper.title,
            paper.author.get_full_name() or paper.author.username,
            paper.author.email,
            paper.submitted_at.strftime('%Y-%m-%d %H:%M'),
            paper.status.title()
        ])
    
    return response

@login_required
def export_accepted_submissions_pdf(request, conf_id):
    """
    Export accepted submissions as PDF.
    """
    from django.http import HttpResponse
    from django.template.loader import get_template
    from django.template import Context
    
    conference = get_object_or_404(Conference, id=conf_id)
    user = request.user
    
    # Ensure only the chair can access
    if conference.chair != user:
        return render(request, 'dashboard/forbidden.html', {
            'message': 'Only the conference chair can access this feature.'
        })
    
    # Get accepted papers
    accepted_papers = Paper.objects.filter(
        conference=conference, 
        status='accepted'
    ).select_related('author').order_by('title')
    
    # For now, return HTML version (you can integrate reportlab for PDF)
    context = {
        'conference': conference,
        'papers': accepted_papers,
        'total_count': accepted_papers.count(),
        'export_type': 'pdf'
    }
    
    response = render(request, 'dashboard/accepted_submissions_export.html', context)
    response['Content-Disposition'] = f'attachment; filename="{conference.acronym}_accepted_submissions.html"'
    return response

@login_required
def reviews_list(request, conf_id):
    """
    Display list of all reviews for the conference.
    """
    conference = get_object_or_404(Conference, id=conf_id)
    user = request.user
    
    # Ensure only the chair can access
    if conference.chair != user:
        return render(request, 'dashboard/forbidden.html', {
            'message': 'Only the conference chair can access this feature.'
        })
    
    # Get all reviews for papers in this conference
    reviews = Review.objects.filter(
        paper__conference=conference
    ).select_related('paper', 'reviewer', 'paper__author').order_by('paper__title', 'reviewer__username')
    
    # Group reviews by paper
    papers_with_reviews = {}
    for review in reviews:
        paper_id = review.paper.id
        if paper_id not in papers_with_reviews:
            papers_with_reviews[paper_id] = {
                'paper': review.paper,
                'reviews': []
            }
        papers_with_reviews[paper_id]['reviews'].append(review)
    
    context = {
        'conference': conference,
        'papers_with_reviews': papers_with_reviews.values(),
        'total_reviews': reviews.count(),
    }
    return render(request, 'dashboard/reviews_list.html', context)

@login_required
def analytics_export(request, conf_id):
    """
    Handle analytics data export in multiple formats (Excel, CSV).
    """
    conference = get_object_or_404(Conference, id=conf_id)
    user = request.user
    
    # Ensure only the chair can access
    if conference.chair != user:
        return render(request, 'dashboard/forbidden.html', {
            'message': 'Only the conference chair can access this feature.'
        })
    
    # Get the export format from the request
    export_format = request.GET.get('format', 'csv').lower()
    
    if export_format == 'excel':
        return export_analytics_excel(request, conf_id)
    else:
        return export_analytics_csv(request, conf_id)

@login_required
def export_analytics_csv(request, conf_id):
    """
    Export analytics data to CSV format.
    """
    import csv
    from django.http import HttpResponse
    from datetime import datetime
    
    conference = get_object_or_404(Conference, id=conf_id)
    user = request.user
    
    # Ensure only the chair can access
    if conference.chair != user:
        return render(request, 'dashboard/forbidden.html', {
            'message': 'Only the conference chair can access this feature.'
        })
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{conference.acronym}_analytics.csv"'
    
    writer = csv.writer(response)
    
    # Write analytics summary
    writer.writerow(['Conference Analytics Report'])
    writer.writerow(['Conference:', conference.name])
    writer.writerow(['Generated:', datetime.now().strftime('%Y-%m-%d %H:%M')])
    writer.writerow([])
    
    # Submission statistics
    writer.writerow(['Submission Statistics'])
    papers = Paper.objects.filter(conference=conference)
    total_submissions = papers.count()
    accepted_papers = papers.filter(status='accepted').count()
    rejected_papers = papers.filter(status='rejected').count()
    pending_papers = papers.filter(status='submitted').count()
    
    writer.writerow(['Total Submissions:', total_submissions])
    writer.writerow(['Accepted:', accepted_papers])
    writer.writerow(['Rejected:', rejected_papers])
    writer.writerow(['Pending:', pending_papers])
    writer.writerow([])
    
    # Paper details
    writer.writerow(['Paper Details'])
    writer.writerow(['Title', 'Author', 'Status', 'Submitted Date', 'Reviews Count'])
    
    for paper in papers.select_related('author'):
        review_count = paper.reviews.count()
        writer.writerow([
            paper.title,
            paper.author.get_full_name() or paper.author.username,
            paper.status.title(),
            paper.submitted_at.strftime('%Y-%m-%d'),
            review_count
        ])
    
    return response

@login_required
def export_analytics_excel(request, conf_id):
    """
    Export analytics data to Excel format.
    """
    import csv
    from django.http import HttpResponse
    from django.db.models import Count
    from datetime import datetime
    
    conference = get_object_or_404(Conference, id=conf_id)
    user = request.user
    
    # Ensure only the chair can access
    if conference.chair != user:
        return render(request, 'dashboard/forbidden.html', {
            'message': 'Only the conference chair can access this feature.'
        })
    
    # Create CSV response (simulating Excel export)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{conference.acronym}_analytics.csv"'
    
    writer = csv.writer(response)
    
    # Write analytics summary
    writer.writerow(['Conference Analytics Report'])
    writer.writerow(['Conference:', conference.name])
    writer.writerow(['Generated:', datetime.now().strftime('%Y-%m-%d %H:%M')])
    writer.writerow([])
    
    # Submission statistics
    writer.writerow(['Submission Statistics'])
    papers = Paper.objects.filter(conference=conference)
    total_submissions = papers.count()
    accepted_papers = papers.filter(status='accepted').count()
    rejected_papers = papers.filter(status='rejected').count()
    pending_papers = papers.filter(status='submitted').count()
    
    writer.writerow(['Total Submissions:', total_submissions])
    writer.writerow(['Accepted:', accepted_papers])
    writer.writerow(['Rejected:', rejected_papers])
    writer.writerow(['Pending:', pending_papers])
    writer.writerow([])
    
    # Paper details
    writer.writerow(['Paper Details'])
    writer.writerow(['Title', 'Author', 'Status', 'Submitted Date', 'Reviews Count'])
    
    for paper in papers.select_related('author'):
        review_count = paper.reviews.count()
        writer.writerow([
            paper.title,
            paper.author.get_full_name() or paper.author.username,
            paper.status.title(),
            paper.submitted_at.strftime('%Y-%m-%d'),
            review_count
        ])
    
    return response

class PCSendEmailView(FormView):
    template_name = 'chair/pc/send_email.html'
    form_class = PCSendEmailForm
    success_url = None  # Will set dynamically

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        conf_id = kwargs.get('conf_id')
        conference = get_object_or_404(Conference, id=conf_id)
        if conference.chair != request.user:
            return render(request, 'dashboard/forbidden.html', {'message': 'Only the conference chair can send emails.'})
        self.conference = conference
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['conference'] = self.conference
        return kwargs

    def get_success_url(self):
        return reverse('dashboard:pc_send_email', kwargs={'conf_id': self.conference.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['conference'] = self.conference
        context['email_logs'] = PCEmailLog.objects.filter(conference=self.conference).order_by('-sent_at')[:20]
        context['email_templates'] = list(EmailTemplate.objects.filter(conference=self.conference).values('id', 'subject', 'body'))
        # Group PC members by role
        from conference.models import UserConferenceRole
        # Chair(s)
        chairs = UserConferenceRole.objects.filter(conference=self.conference, role='chair').select_related('user')
        # Ordinary PC members (exclude chair)
        ordinary_pc_members = UserConferenceRole.objects.filter(conference=self.conference, role='pc_member').select_related('user').exclude(user=self.conference.chair)
        context['chairs'] = [ucr.user for ucr in chairs]
        context['ordinary_pc_members'] = [ucr.user for ucr in ordinary_pc_members]
        # For AJAX: provide recipient list for the selected type
        form = context.get('form')
        if form:
            context['recipients_html'] = render_to_string('chair/pc/recipients_field.html', {'form': form, 'chairs': context['chairs'], 'ordinary_pc_members': context['ordinary_pc_members']})
        return context

    def post(self, request, *args, **kwargs):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' and 'recipients' not in request.POST:
            form = self.get_form_class()(request.POST, conference=self.conference)
            recipients_html = render_to_string('chair/pc/recipients_field.html', {'form': form})
            return JsonResponse({'recipients_html': recipients_html})

        recipients_raw = request.POST.get('recipients', '')
        recipient_ids = [rid for rid in recipients_raw.split(',') if rid.strip()]
        users = User.objects.filter(id__in=recipient_ids)
        subject = request.POST.get('subject', '').strip()
        body = request.POST.get('body', '').strip()
        attachment = request.FILES.get('attachment')
        errors = []
        sent_count = 0
        # If not confirmed, show preview page
        if 'confirm_send' not in request.POST:
            return render(request, 'chair/pc/send_email_confirm.html', {
                'conference': self.conference,
                'subject': subject,
                'body': body,
                'attachment': attachment,
                'recipients': users,
                'recipients_raw': recipients_raw,
            })
        # Actually send emails
        if not users:
            messages.error(request, 'Please select at least one PC member to send the email.')
            return self.form_invalid(self.get_form_class()(request.POST, request.FILES, conference=self.conference))
        if not subject or not body:
            messages.error(request, 'Subject and message are required.')
            return self.form_invalid(self.get_form_class()(request.POST, request.FILES, conference=self.conference))
        for user in users:
            personalized_body = body.replace('{*NAME*}', user.get_full_name() or user.username).replace('{{name}}', user.get_full_name() or user.username)
            try:
                email_msg = EmailMessage(
                    subject=subject,
                    body=personalized_body,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER),
                    to=[user.email],
                )
                if attachment:
                    email_msg.attach(attachment.name, attachment.read(), attachment.content_type)
                email_msg.send(fail_silently=False)
                sent_count += 1
                # Log the email
                PCEmailLog.objects.create(
                    subject=subject,
                    body=personalized_body,
                    recipients=user.email,
                    conference=self.conference,
                    sender=request.user,
                    attachment_name=attachment.name if attachment else '',
                )
            except Exception as e:
                errors.append(f"Failed to send to {user.email}: {e}")
        if sent_count:
            messages.success(request, f"Email sent to {sent_count} PC member(s)." + (f" Errors: {'; '.join(errors)}" if errors else ''))
        else:
            messages.error(request, 'No emails sent. ' + ('; '.join(errors) if errors else ''))
        return redirect(self.get_success_url())

# AJAX endpoint for template autofill
@login_required
@csrf_exempt
def get_email_template(request, conf_id):
    template_id = request.GET.get('template_id')
    template = EmailTemplate.objects.filter(conference_id=conf_id, id=template_id).first()
    if template:
        return JsonResponse({'subject': template.subject, 'body': template.body})
    return JsonResponse({'subject': '', 'body': ''})

@login_required
@csrf_exempt
def get_sample_recipient_data(request, conf_id):
    recipient_type = request.GET.get('recipient_type', 'pc')
    recipient_id = request.GET.get('recipient_id')
    conference = get_object_or_404(Conference, id=conf_id)
    user = None
    paper = None
    if recipient_id:
        user = User.objects.filter(id=recipient_id).first()
    else:
        # Get a sample user for the role
        if recipient_type == 'author':
            user = User.objects.filter(userconferencerole__conference=conference, userconferencerole__role='author').first()
        elif recipient_type == 'subreviewer':
            user = User.objects.filter(userconferencerole__conference=conference, userconferencerole__role='subreviewer').first()
        else:
            user = User.objects.filter(userconferencerole__conference=conference, userconferencerole__role='pc_member').first()
    if user:
        # Get a sample paper for the user if author
        if recipient_type == 'author':
            paper = Paper.objects.filter(author=user, conference=conference).first()
        data = {
            'name': user.get_full_name() or user.username,
            'email': user.email,
            'submission_title': paper.title if paper else '',
            'conference_name': conference.name,
            'conference_acronym': conference.acronym,
            'conference_description': conference.description,
            'deadline': str(conference.paper_submission_deadline) if conference.paper_submission_deadline else '',
        }
    else:
        data = {
            'name': 'Sample User',
            'email': 'sample@example.com',
            'submission_title': 'Sample Paper',
            'conference_name': conference.name,
            'conference_acronym': conference.acronym,
            'conference_description': conference.description,
            'deadline': str(conference.paper_submission_deadline) if conference.paper_submission_deadline else '',
        }
    return JsonResponse(data)

@login_required
def all_submissions(request, conf_id):
    conference = get_object_or_404(Conference, id=conf_id)
    user = request.user
    
    # Get all papers for this conference
    papers = Paper.objects.filter(conference=conference).select_related('author').prefetch_related('reviews', 'subreviewer_invites')
    
    # Section 1: Submissions assigned to me and accepted by a subreviewer
    assigned_with_accepted_subreviewers = []
    
    # Section 2: Submissions reviewed by me
    reviewed_by_me = []
    
    for paper in papers:
        # Check if user is assigned to review this paper
        user_review = paper.reviews.filter(reviewer=user).first()
        
        # Get subreviewer invites for this paper
        subreviewer_invites = paper.subreviewer_invites.all()
        accepted_subreviewers = [invite for invite in subreviewer_invites if invite.status == 'accepted']
        
        # Check if user has reviewed this paper
        if user_review and user_review.decision:
            reviewed_by_me.append({
                'paper': paper,
                'review': user_review,
                'subreviewers': accepted_subreviewers,
                'all_subreviewers': subreviewer_invites
            })
        # Check if user is assigned but hasn't reviewed yet, and has accepted subreviewers
        elif user_review and not user_review.decision and accepted_subreviewers:
            assigned_with_accepted_subreviewers.append({
                'paper': paper,
                'review': user_review,
                'subreviewers': accepted_subreviewers,
                'all_subreviewers': subreviewer_invites
            })
    
    nav_items = [
        "Submissions", "Reviews", "Status", "PC", "Events",
        "Email", "Administration", "Conference", "News", "papersetu"
    ]
    active_tab = "Reviews"
    review_dropdown_items = [
        {'label': 'All submissions', 'url': reverse('dashboard:all_submissions', args=[conference.id])},
        {'label': 'Assigned to me', 'url': reverse('dashboard:assigned_to_me', args=[conference.id])},
        {'label': 'Subreviewers', 'url': reverse('dashboard:subreviewers', args=[conference.id])},
        {'label': 'Pool of subreviewers', 'url': reverse('dashboard:pool_subreviewers', args=[conference.id])},
        {'label': 'By PC member', 'url': reverse('dashboard:by_pc_member', args=[conference.id])},
        {'label': 'By submission', 'url': reverse('dashboard:by_submission', args=[conference.id])},
        {'label': 'Delete', 'url': reverse('dashboard:delete_review', args=[conference.id])},
        {'label': 'Send to authors', 'url': reverse('dashboard:send_to_authors', args=[conference.id])},
        {'label': 'Missing reviews', 'url': reverse('dashboard:missing_reviews', args=[conference.id])},
    ]
    return render(request, 'dashboard/all_submissions.html', {
        'conf_id': conf_id,
        'conference': conference,
        'nav_items': nav_items,
        'active_tab': active_tab,
        'review_dropdown_items': review_dropdown_items,
        'assigned_with_accepted_subreviewers': assigned_with_accepted_subreviewers,
        'reviewed_by_me': reviewed_by_me,
        'user': user,
    })

@login_required
def assigned_to_me(request, conf_id):
    conference = get_object_or_404(Conference, id=conf_id)
    user = request.user
    
    # Get papers assigned to the current user for review
    assigned_papers = []
    user_reviews = Review.objects.filter(
        paper__conference=conference,
        reviewer=user
    ).select_related('paper', 'paper__author').prefetch_related('paper__subreviewer_invites')
    
    for review in user_reviews:
        # Get subreviewer information for this paper
        subreviewer_invites = review.paper.subreviewer_invites.all()
        
        assigned_papers.append({
            'paper': review.paper,
            'review': review,
            'subreviewers': subreviewer_invites
        })
    
    # Calculate statistics
    pending_count = sum(1 for assignment in assigned_papers if not assignment['review'].decision)
    completed_count = sum(1 for assignment in assigned_papers if assignment['review'].decision)
    
    nav_items = [
        "Submissions", "Reviews", "Status", "PC", "Events",
        "Email", "Administration", "Conference", "News", "papersetu"
    ]
    active_tab = "Reviews"
    review_dropdown_items = [
        {'label': 'All submissions', 'url': reverse('dashboard:all_submissions', args=[conference.id])},
        {'label': 'Assigned to me', 'url': reverse('dashboard:assigned_to_me', args=[conference.id])},
        {'label': 'Subreviewers', 'url': reverse('dashboard:subreviewers', args=[conference.id])},
        {'label': 'Pool of subreviewers', 'url': reverse('dashboard:pool_subreviewers', args=[conference.id])},
        {'label': 'By PC member', 'url': reverse('dashboard:by_pc_member', args=[conference.id])},
        {'label': 'By submission', 'url': reverse('dashboard:by_submission', args=[conference.id])},
        {'label': 'Delete', 'url': reverse('dashboard:delete_review', args=[conference.id])},
        {'label': 'Send to authors', 'url': reverse('dashboard:send_to_authors', args=[conference.id])},
        {'label': 'Missing reviews', 'url': reverse('dashboard:missing_reviews', args=[conference.id])},
    ]
    return render(request, 'dashboard/assigned_to_me.html', {
        'conf_id': conf_id,
        'conference': conference,
        'nav_items': nav_items,
        'active_tab': active_tab,
        'review_dropdown_items': review_dropdown_items,
        'assigned_papers': assigned_papers,
        'pending_count': pending_count,
        'completed_count': completed_count,
    })

@login_required
def subreviewers(request, conf_id):
    conference = get_object_or_404(Conference, id=conf_id)
    if not (conference.chair == request.user or UserConferenceRole.objects.filter(user=request.user, conference=conference, role='pc_member').exists()):
        return render(request, 'dashboard/forbidden.html', {'message': 'You do not have permission to manage subreviewers.'})

    search_query = request.GET.get('search', '').strip()
    papers = Paper.objects.filter(conference=conference)
    all_users = User.objects.exclude(id=conference.chair.id)
    if search_query:
        all_users = all_users.filter(username__icontains=search_query) | all_users.filter(email__icontains=search_query)

    # Handle invite action
    message = None
    message_type = None
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'invite':
            paper_id = request.POST.get('paper_id')
            user_id = request.POST.get('user_id')
            email = request.POST.get('email')
            template_body = request.POST.get('template_body')
            if paper_id and user_id and email:
                paper = Paper.objects.get(id=paper_id)
                subreviewer = User.objects.get(id=user_id)
                # Prevent duplicate invite
                if SubreviewerInvite.objects.filter(paper=paper, subreviewer=subreviewer).exists():
                    message = f"This subreviewer has already been invited for this paper."
                    message_type = 'error'
                else:
                    token = get_random_string(48)
                    invite = SubreviewerInvite.objects.create(
                        paper=paper,
                        subreviewer=subreviewer,
                        invited_by=request.user,
                        email=email,
                        token=token
                    )
                    UserConferenceRole.objects.get_or_create(user=subreviewer, conference=conference, role='subreviewer')
                    body = f"Dear {subreviewer.get_full_name() or subreviewer.username},\n\nYou have been assigned a paper for review (\"{paper.title}\") in the conference '{conference.name}'. Please log in to your dashboard to accept or reject the request.\n\nBest regards,\n{request.user.get_full_name() or request.user.username}\nConference Chair/PC Member"
                    send_mail(
                        subject=f"Paper Review Assignment: '{paper.title}'",
                        message=body,
                        from_email=None,
                        recipient_list=[email],
                    )
                    PCEmailLog.objects.create(
                        subject=f"Paper Review Assignment: '{paper.title}'",
                        body=body,
                        recipients=email,
                        conference=conference,
                        sender=request.user,
                        attachment_name='',
                    )
                    message = f"Assignment email sent to {subreviewer.get_full_name() or subreviewer.username} for paper '{paper.title}'."
                    message_type = 'success'
            else:
                message = "Please select a paper, subreviewer, and provide an email."
                message_type = 'error'
        elif action == 'bulk_invite':
            paper_id = request.POST.get('paper_id')
            bulk_list = request.POST.get('bulk_invitation_list', '').strip().split('\n')
            paper = Paper.objects.get(id=paper_id)
            success_count = 0
            error_count = 0
            error_messages = []
            for line in bulk_list:
                if not line.strip():
                    continue
                # Format: Name <email>
                if '<' in line and '>' in line:
                    name = line.split('<')[0].strip()
                    email = line.split('<')[1].split('>')[0].strip()
                else:
                    error_messages.append(f'Invalid format: {line}')
                    error_count += 1
                    continue
                try:
                    subreviewer = User.objects.filter(email=email).first()
                    if not subreviewer:
                        error_messages.append(f'User not found: {email}')
                        error_count += 1
                        continue
                    # Check for duplicate invite
                    if SubreviewerInvite.objects.filter(paper=paper, subreviewer=subreviewer).exists():
                        error_messages.append(f'Already invited: {email}')
                        error_count += 1
                        continue
                    token = get_random_string(48)
                    invite = SubreviewerInvite.objects.create(
                        paper=paper,
                        subreviewer=subreviewer,
                        invited_by=request.user,
                        email=email,
                        token=token
                    )
                    UserConferenceRole.objects.get_or_create(user=subreviewer, conference=conference, role='subreviewer')
                    subject = f"Paper Review Assignment: '{paper.title}'"
                    message_body = f"Dear {name},\n\nYou have been assigned a paper for review (\"{paper.title}\") in the conference '{conference.name}'. Please log in to your dashboard to accept or reject the request.\n\nBest regards,\n{request.user.get_full_name() or request.user.username}\nConference Chair"
                    send_mail(subject, message_body, None, [email])
                    success_count += 1
                except Exception as e:
                    error_messages.append(f'Error for {email}: {str(e)}')
                    error_count += 1
            message = f"Bulk invitation complete. {success_count} sent, {error_count} errors."
            if error_messages:
                message += '\n' + '\n'.join(error_messages[:5])
                if len(error_messages) > 5:
                    message += f'\n... and {len(error_messages) - 5} more errors.'
            message_type = 'success' if success_count > 0 else 'error'

    # List all invites for this conference
    invites = SubreviewerInvite.objects.filter(paper__conference=conference).select_related('paper', 'subreviewer', 'invited_by')

    # Get authors for this conference
    authors = User.objects.filter(papers__conference=conference).distinct()
    
    # Get reviewers for this conference
    reviewers = User.objects.filter(reviews__paper__conference=conference).distinct()
    
    # Get review invites for this conference
    review_invites = ReviewInvite.objects.filter(conference=conference)
    
    # Get available reviewers (users who can be invited as subreviewers)
    available_reviewers = User.objects.exclude(
        id__in=UserConferenceRole.objects.filter(conference=conference).values_list('user_id', flat=True)
    ).exclude(id=conference.chair.id)
    
    # Get all users for the dropdown (excluding chair)
    all_users = User.objects.exclude(id=conference.chair.id)
    
    # Initialize message variables
    assign_message = None
    invite_message = message  # Use the message from the POST handling above
    invite_url = None
    
    # Default template for subreviewer invitation
    default_template = f"""Dear {{ subreviewer_name }},

You have been invited to review the paper "{{ paper_title }}" for {conference.name}.

Please click the following link to accept or decline this invitation:
{{ invite_url }}

Best regards,
{conference.chair.get_full_name() or conference.chair.username}
Conference Chair"""

    # Add nav bar context for chair dashboard
    nav_items = [
        "Submissions", "Reviews", "Status", "PC", "Events",
        "Email", "Administration", "Conference", "News", "papersetu"
    ]
    active_tab = "Reviews"
    review_dropdown_items = [
        {'label': 'All submissions', 'url': reverse('dashboard:all_submissions', args=[conference.id])},
        {'label': 'Assigned to me', 'url': reverse('dashboard:assigned_to_me', args=[conference.id])},
        {'label': 'Subreviewers', 'url': reverse('dashboard:subreviewers', args=[conference.id])},
        {'label': 'Pool of subreviewers', 'url': reverse('dashboard:pool_subreviewers', args=[conference.id])},
        {'label': 'By PC member', 'url': reverse('dashboard:by_pc_member', args=[conference.id])},
        {'label': 'By submission', 'url': reverse('dashboard:by_submission', args=[conference.id])},
        {'label': 'Delete', 'url': reverse('dashboard:delete_review', args=[conference.id])},
        {'label': 'Send to authors', 'url': reverse('dashboard:send_to_authors', args=[conference.id])},
        {'label': 'Missing reviews', 'url': reverse('dashboard:missing_reviews', args=[conference.id])},
    ]
    context = {
        'conference': conference,
        'papers': papers,
        'authors': authors,
        'reviewers': reviewers,
        'review_invites': review_invites,
        'available_reviewers': available_reviewers,
        'assign_message': assign_message,
        'invite_message': invite_message,
        'invite_url': invite_url,
        'search_query': search_query,
        'nav_items': nav_items,
        'active_tab': active_tab,
        'review_dropdown_items': review_dropdown_items,
        'invites': invites,  # Add the invites to context
        'message': message,  # Add the message to context
        'message_type': message_type,  # Add the message type to context
        'all_users': all_users,  # Add all users for dropdown
        'default_template': default_template,  # Add default template
    }
    return render(request, 'dashboard/subreviewers.html', context)

@login_required
def pool_subreviewers(request, conf_id):
    conference = get_object_or_404(Conference, id=conf_id)
    user = request.user
    
    # Get search and filter parameters
    search_query = request.GET.get('search', '').strip()
    selected_expertise = request.GET.get('expertise', '')
    selected_availability = request.GET.get('availability', '')
    
    # Get all subreviewers for this conference
    subreviewers = User.objects.filter(
        userconferencerole__conference=conference,
        userconferencerole__role='subreviewer'
    ).select_related('reviewer_profile').prefetch_related('reviews', 'subreviewer_invites')
    
    # Apply search filter
    if search_query:
        subreviewers = subreviewers.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Apply expertise filter
    if selected_expertise:
        subreviewers = subreviewers.filter(reviewer_profile__expertise=selected_expertise)
    
    # Apply availability filter
    if selected_availability:
        if selected_availability == 'available':
            subreviewers = subreviewers.annotate(
                current_assignments=Count('subreviewer_invites', filter=Q(subreviewer_invites__status='accepted'))
            ).filter(current_assignments__lt=3)
        elif selected_availability == 'busy':
            subreviewers = subreviewers.annotate(
                current_assignments=Count('subreviewer_invites', filter=Q(subreviewer_invites__status='accepted'))
            ).filter(current_assignments__gte=3)
    
    # Add current assignment count for all subreviewers
    for subreviewer in subreviewers:
        subreviewer.current_assignments = subreviewer.subreviewer_invites.filter(status='accepted').count()
    
    # Get expertise choices
    expertise_choices = ReviewerPool.objects.values_list('expertise', flat=True).distinct()
    
    # Get available papers for assignment
    available_papers = Paper.objects.filter(conference=conference).select_related('author')
    
    # Handle assignment form submission
    if request.method == 'POST':
        subreviewer_id = request.POST.get('subreviewer_id')
        paper_id = request.POST.get('paper_id')
        email = request.POST.get('email')
        
        if subreviewer_id and paper_id and email:
            try:
                subreviewer = User.objects.get(id=subreviewer_id)
                paper = Paper.objects.get(id=paper_id, conference=conference)
                
                # Create subreviewer invite
                token = get_random_string(48)
                invite = SubreviewerInvite.objects.create(
                    paper=paper,
                    subreviewer=subreviewer,
                    invited_by=user,
                    email=email,
                    token=token
                )
                
                # Send assignment email
                subject = f"Paper Review Assignment: '{paper.title}'"
                message = f"""Dear {subreviewer.get_full_name() or subreviewer.username},

You have been assigned a paper for review ("{paper.title}") in the conference '{conference.name}'. 

Please log in to your dashboard to accept or reject the request.

Best regards,
{user.get_full_name() or user.username}
Conference Chair/PC Member"""
                
                send_mail(subject, message, None, [email])
                
                messages.success(request, f'Assignment sent to {subreviewer.get_full_name() or subreviewer.username} for paper "{paper.title}"')
                
            except (User.DoesNotExist, Paper.DoesNotExist):
                messages.error(request, 'Invalid subreviewer or paper selected.')
            except Exception as e:
                messages.error(request, f'Error creating assignment: {str(e)}')
    
    nav_items = [
        "Submissions", "Reviews", "Status", "PC", "Events",
        "Email", "Administration", "Conference", "News", "papersetu"
    ]
    active_tab = "Reviews"
    review_dropdown_items = [
        {'label': 'All submissions', 'url': reverse('dashboard:all_submissions', args=[conference.id])},
        {'label': 'Assigned to me', 'url': reverse('dashboard:assigned_to_me', args=[conference.id])},
        {'label': 'Subreviewers', 'url': reverse('dashboard:subreviewers', args=[conference.id])},
        {'label': 'Pool of subreviewers', 'url': reverse('dashboard:pool_subreviewers', args=[conference.id])},
        {'label': 'By PC member', 'url': reverse('dashboard:by_pc_member', args=[conference.id])},
        {'label': 'By submission', 'url': reverse('dashboard:by_submission', args=[conference.id])},
        {'label': 'Delete', 'url': reverse('dashboard:delete_review', args=[conference.id])},
        {'label': 'Send to authors', 'url': reverse('dashboard:send_to_authors', args=[conference.id])},
        {'label': 'Missing reviews', 'url': reverse('dashboard:missing_reviews', args=[conference.id])},
    ]
    return render(request, 'dashboard/pool_subreviewers.html', {
        'conf_id': conf_id,
        'conference': conference,
        'nav_items': nav_items,
        'active_tab': active_tab,
        'review_dropdown_items': review_dropdown_items,
        'subreviewers': subreviewers,
        'search_query': search_query,
        'selected_expertise': selected_expertise,
        'selected_availability': selected_availability,
        'expertise_choices': expertise_choices,
        'available_papers': available_papers,
    })

@login_required
def by_pc_member(request, conf_id):
    conference = get_object_or_404(Conference, id=conf_id)
    
    # Get all PC members for this conference
    pc_members = UserConferenceRole.objects.filter(
        conference=conference,
        role='pc_member'
    ).select_related('user').prefetch_related('user__reviews')
    
    pc_members_data = []
    total_completed = 0
    total_pending = 0
    total_assignments = 0
    
    for pc_member in pc_members:
        # Get all reviews by this PC member for this conference
        reviews = Review.objects.filter(
            reviewer=pc_member.user,
            paper__conference=conference
        ).select_related('paper', 'paper__author')
        
        assignments = []
        completed_reviews = 0
        pending_reviews = 0
        
        for review in reviews:
            assignments.append({
                'paper': review.paper,
                'review': review
            })
            
            if review.decision:
                completed_reviews += 1
            else:
                pending_reviews += 1
        
        pc_members_data.append({
            'user': pc_member.user,
            'assignments': assignments,
            'completed_reviews': completed_reviews,
            'pending_reviews': pending_reviews,
            'total_assignments': len(assignments)
        })
        
        total_completed += completed_reviews
        total_pending += pending_reviews
        total_assignments += len(assignments)
    
    nav_items = [
        "Submissions", "Reviews", "Status", "PC", "Events",
        "Email", "Administration", "Conference", "News", "papersetu"
    ]
    active_tab = "Reviews"
    review_dropdown_items = [
        {'label': 'All submissions', 'url': reverse('dashboard:all_submissions', args=[conference.id])},
        {'label': 'Assigned to me', 'url': reverse('dashboard:assigned_to_me', args=[conference.id])},
        {'label': 'Subreviewers', 'url': reverse('dashboard:subreviewers', args=[conference.id])},
        {'label': 'Pool of subreviewers', 'url': reverse('dashboard:pool_subreviewers', args=[conference.id])},
        {'label': 'By PC member', 'url': reverse('dashboard:by_pc_member', args=[conference.id])},
        {'label': 'By submission', 'url': reverse('dashboard:by_submission', args=[conference.id])},
        {'label': 'Delete', 'url': reverse('dashboard:delete_review', args=[conference.id])},
        {'label': 'Send to authors', 'url': reverse('dashboard:send_to_authors', args=[conference.id])},
        {'label': 'Missing reviews', 'url': reverse('dashboard:missing_reviews', args=[conference.id])},
    ]
    return render(request, 'dashboard/by_pc_member.html', {
        'conf_id': conf_id,
        'conference': conference,
        'nav_items': nav_items,
        'active_tab': active_tab,
        'review_dropdown_items': review_dropdown_items,
        'pc_members': pc_members_data,
        'total_completed': total_completed,
        'total_pending': total_pending,
        'total_assignments': total_assignments,
    })

@login_required
def by_submission(request, conf_id):
    conference = get_object_or_404(Conference, id=conf_id)
    
    # Get all submissions for this conference
    papers = Paper.objects.filter(conference=conference).select_related('author').prefetch_related('reviews', 'subreviewer_invites')
    
    submissions_data = []
    total_submitted = 0
    total_missing = 0
    total_reviewers = 0
    
    for paper in papers:
        # Get all reviews for this paper (both PC member and subreviewer reviews)
        reviews = []
        
        # PC member reviews
        pc_reviews = Review.objects.filter(paper=paper).select_related('reviewer')
        for review in pc_reviews:
            reviews.append({
                'review': review,
                'reviewer': review.reviewer,
                'is_subreviewer': False,
                'role': 'PC Member'
            })
        
        # Subreviewer reviews (from accepted invites)
        subreviewer_invites = paper.subreviewer_invites.filter(status='accepted').select_related('subreviewer')
        for invite in subreviewer_invites:
            # Check if there's a review from this subreviewer
            subreview = Review.objects.filter(paper=paper, reviewer=invite.subreviewer).first()
            if subreview:
                reviews.append({
                    'review': subreview,
                    'reviewer': invite.subreviewer,
                    'is_subreviewer': True,
                    'role': 'Subreviewer'
                })
            else:
                # Add placeholder for missing subreviewer review
                reviews.append({
                    'review': None,
                    'reviewer': invite.subreviewer,
                    'is_subreviewer': True,
                    'role': 'Subreviewer'
                })
        
        # Calculate statistics
        completed_reviews = sum(1 for r in reviews if r['review'] and r['review'].decision)
        pending_reviews = len(reviews) - completed_reviews
        
        submissions_data.append({
            'paper': paper,
            'reviews': reviews,
            'completed_reviews': completed_reviews,
            'pending_reviews': pending_reviews,
            'total_reviewers': len(reviews)
        })
        
        total_submitted += completed_reviews
        total_missing += pending_reviews
        total_reviewers += len(reviews)
    
    nav_items = [
        "Submissions", "Reviews", "Status", "PC", "Events",
        "Email", "Administration", "Conference", "News", "papersetu"
    ]
    active_tab = "Reviews"
    review_dropdown_items = [
        {'label': 'All submissions', 'url': reverse('dashboard:all_submissions', args=[conference.id])},
        {'label': 'Assigned to me', 'url': reverse('dashboard:assigned_to_me', args=[conference.id])},
        {'label': 'Subreviewers', 'url': reverse('dashboard:subreviewers', args=[conference.id])},
        {'label': 'Pool of subreviewers', 'url': reverse('dashboard:pool_subreviewers', args=[conference.id])},
        {'label': 'By PC member', 'url': reverse('dashboard:by_pc_member', args=[conference.id])},
        {'label': 'By submission', 'url': reverse('dashboard:by_submission', args=[conference.id])},
        {'label': 'Delete', 'url': reverse('dashboard:delete_review', args=[conference.id])},
        {'label': 'Send to authors', 'url': reverse('dashboard:send_to_authors', args=[conference.id])},
        {'label': 'Missing reviews', 'url': reverse('dashboard:missing_reviews', args=[conference.id])},
    ]
    return render(request, 'dashboard/by_submission.html', {
        'conf_id': conf_id,
        'conference': conference,
        'nav_items': nav_items,
        'active_tab': active_tab,
        'review_dropdown_items': review_dropdown_items,
        'submissions': submissions_data,
        'total_submitted': total_submitted,
        'total_missing': total_missing,
        'total_reviewers': total_reviewers,
    })

@login_required
def delete_review(request, conf_id):
    conference = get_object_or_404(Conference, id=conf_id)
    user = request.user
    
    # Check if user is chair (either direct chair field or UserConferenceRole)
    is_direct_chair = conference.chair == user
    is_chair_role = UserConferenceRole.objects.filter(user=user, conference=conference, role='chair').exists()
    is_chair = is_direct_chair or is_chair_role
    
    # Allow access for conference chair, staff, or superuser
    if not (is_chair or user.is_staff or user.is_superuser):
        nav_items = [
            "Submissions", "Reviews", "Status", "PC", "Events",
            "Email", "Administration", "Conference", "News", "papersetu"
        ]
        active_tab = "Reviews"
        review_dropdown_items = [
            {'label': 'All submissions', 'url': reverse('dashboard:all_submissions', args=[conference.id])},
            {'label': 'Assigned to me', 'url': reverse('dashboard:assigned_to_me', args=[conference.id])},
            {'label': 'Subreviewers', 'url': reverse('dashboard:subreviewers', args=[conference.id])},
            {'label': 'Pool of subreviewers', 'url': reverse('dashboard:pool_subreviewers', args=[conference.id])},
            {'label': 'By PC member', 'url': reverse('dashboard:by_pc_member', args=[conference.id])},
            {'label': 'By submission', 'url': reverse('dashboard:by_submission', args=[conference.id])},
            {'label': 'Delete', 'url': reverse('dashboard:delete_review', args=[conference.id])},
            {'label': 'Send to authors', 'url': reverse('dashboard:send_to_authors', args=[conference.id])},
            {'label': 'Missing reviews', 'url': reverse('dashboard:missing_reviews', args=[conference.id])},
        ]
        return render(request, 'dashboard/delete_review.html', {
            'conf_id': conf_id,
            'conference': conference,
            'nav_items': nav_items,
            'active_tab': active_tab,
            'review_dropdown_items': review_dropdown_items,
            'is_chair': is_chair,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
        })
    
    # Handle review deletion
    if request.method == 'POST':
        review_id = request.POST.get('review_id')
        if review_id:
            try:
                review = Review.objects.get(id=review_id, paper__conference=conference)
                paper_title = review.paper.title
                reviewer_name = review.reviewer.get_full_name() or review.reviewer.username
                
                # Delete the review
                review.delete()
                
                messages.success(request, f'Review by {reviewer_name} for "{paper_title}" has been deleted successfully.')
                
            except Review.DoesNotExist:
                messages.error(request, 'Review not found.')
            except Exception as e:
                messages.error(request, f'Error deleting review: {str(e)}')
    
    # Get all reviews for this conference
    reviews = Review.objects.filter(
        paper__conference=conference
    ).select_related('paper', 'paper__author', 'reviewer')
    
    nav_items = [
        "Submissions", "Reviews", "Status", "PC", "Events",
        "Email", "Administration", "Conference", "News", "papersetu"
    ]
    active_tab = "Reviews"
    review_dropdown_items = [
        {'label': 'All submissions', 'url': reverse('dashboard:all_submissions', args=[conference.id])},
        {'label': 'Assigned to me', 'url': reverse('dashboard:assigned_to_me', args=[conference.id])},
        {'label': 'Subreviewers', 'url': reverse('dashboard:subreviewers', args=[conference.id])},
        {'label': 'Pool of subreviewers', 'url': reverse('dashboard:pool_subreviewers', args=[conference.id])},
        {'label': 'By PC member', 'url': reverse('dashboard:by_pc_member', args=[conference.id])},
        {'label': 'By submission', 'url': reverse('dashboard:by_submission', args=[conference.id])},
        {'label': 'Delete', 'url': reverse('dashboard:delete_review', args=[conference.id])},
        {'label': 'Send to authors', 'url': reverse('dashboard:send_to_authors', args=[conference.id])},
        {'label': 'Missing reviews', 'url': reverse('dashboard:missing_reviews', args=[conference.id])},
    ]
    return render(request, 'dashboard/delete_review.html', {
        'conf_id': conf_id,
        'conference': conference,
        'nav_items': nav_items,
        'active_tab': active_tab,
        'review_dropdown_items': review_dropdown_items,
        'reviews': reviews,
        'is_chair': is_chair,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
    })

@login_required
def send_to_authors(request, conf_id):
    conference = get_object_or_404(Conference, id=conf_id)
    nav_items = [
        "Submissions", "Reviews", "Status", "PC", "Events",
        "Email", "Administration", "Conference", "News", "papersetu"
    ]
    active_tab = "Reviews"
    review_dropdown_items = [
        {'label': 'All submissions', 'url': reverse('dashboard:all_submissions', args=[conference.id])},
        {'label': 'Assigned to me', 'url': reverse('dashboard:assigned_to_me', args=[conference.id])},
        {'label': 'Subreviewers', 'url': reverse('dashboard:subreviewers', args=[conference.id])},
        {'label': 'Pool of subreviewers', 'url': reverse('dashboard:pool_subreviewers', args=[conference.id])},
        {'label': 'By PC member', 'url': reverse('dashboard:by_pc_member', args=[conference.id])},
        {'label': 'By submission', 'url': reverse('dashboard:by_submission', args=[conference.id])},
        {'label': 'Delete', 'url': reverse('dashboard:delete_review', args=[conference.id])},
        {'label': 'Send to authors', 'url': reverse('dashboard:send_to_authors', args=[conference.id])},
        {'label': 'Missing reviews', 'url': reverse('dashboard:missing_reviews', args=[conference.id])},
    ]
    # Fetch all submissions for this conference
    papers = Paper.objects.filter(conference=conference).select_related('author').order_by('id')
    submissions = []
    for paper in papers:
        submissions.append({
            'id': paper.id,
            'title': paper.title,
            'decision': paper.status.upper(),
            'author_name': paper.author.get_full_name() or paper.author.username,
            'author_email': paper.author.email,
            'paper_id': paper.paper_id,
            'detail_url': reverse('dashboard:view_paper_submission', args=[conference.id, paper.id]),
        })
    # Handle POST: send email to selected authors
    if request.method == 'POST':
        from django.core.mail import EmailMessage
        import logging
        subject = request.POST.get('subject', '')
        message = request.POST.get('message', '')
        send_all = request.POST.get('send_all_authors') == 'on'
        selected_paper_ids = request.POST.getlist('selected_papers')
        # Get selected authors
        selected_authors = []
        if send_all:
            selected_authors = [{'name': sub['author_name'], 'email': sub['author_email'], 'paper_id': sub['paper_id']} for sub in submissions]
        else:
            for sub in submissions:
                if str(sub['id']) in selected_paper_ids:
                    selected_authors.append({'name': sub['author_name'], 'email': sub['author_email'], 'paper_id': sub['paper_id']})
        # Remove duplicates
        seen_emails = set()
        unique_authors = []
        for a in selected_authors:
            if a['email'] not in seen_emails:
                unique_authors.append(a)
                seen_emails.add(a['email'])
        # Handle attachment
        attachment = request.FILES.get('attachment')
        # Send email to each author
        for author in unique_authors:
            personalized_message = message.replace('{*NAME*}', author['name']).replace('{*paperid*}', author['paper_id'])
            email_obj = EmailMessage(
                subject=subject,
                body=personalized_message,
                to=[author['email']],
            )
            if attachment:
                email_obj.attach(attachment.name, attachment.read(), attachment.content_type)
            email_obj.send(fail_silently=False)
            print(f"[SEND_TO_AUTHOR] Sent email to: {author['email']} (subject: {subject})")
            # Log the author notification email
            PCEmailLog.objects.create(
                subject=subject,
                body=personalized_message,
                recipients=author['email'],
                conference=conference,
                sender=request.user,
                attachment_name=attachment.name if attachment else '',
            )
        # Show popup and redirect
        author_names = ', '.join([a['name'] for a in unique_authors]) or 'No authors selected'
        return render(request, 'dashboard/send_to_authors.html', {
            'conf_id': conf_id,
            'conference': conference,
            'nav_items': nav_items,
            'active_tab': active_tab,
            'review_dropdown_items': review_dropdown_items,
            'submissions': submissions,
            'show_popup': True,
            'popup_names': author_names,
        })
    # For GET: set default message
    default_message = "Dear author {*NAME*} of Paper {*paperid*},"
    return render(request, 'dashboard/send_to_authors.html', {
        'conf_id': conf_id,
        'conference': conference,
        'nav_items': nav_items,
        'active_tab': active_tab,
        'review_dropdown_items': review_dropdown_items,
        'submissions': submissions,
        'default_message': default_message,
    })

@login_required
def missing_reviews(request, conf_id):
    conference = get_object_or_404(Conference, id=conf_id)
    user = request.user
    
    # Handle reminder form submission
    if request.method == 'POST':
        review_id = request.POST.get('review_id')
        custom_message = request.POST.get('custom_message', '')
        
        if review_id:
            try:
                review = Review.objects.get(id=review_id, paper__conference=conference)
                
                # Send reminder email
                subject = f"Review Reminder: '{review.paper.title}'"
                message = f"""Dear {review.reviewer.get_full_name() or review.reviewer.username},

This is a friendly reminder that you have a pending review for the paper "{review.paper.title}" in the conference '{conference.name}'.

Please log in to your dashboard to complete your review as soon as possible.

{f'Additional message: {custom_message}' if custom_message else ''}

Best regards,
{user.get_full_name() or user.username}
Conference Chair/PC Member"""
                
                send_mail(subject, message, None, [review.reviewer.email])
                
                messages.success(request, f'Reminder sent to {review.reviewer.get_full_name() or review.reviewer.username} for paper "{review.paper.title}"')
                
            except Review.DoesNotExist:
                messages.error(request, 'Review not found.')
            except Exception as e:
                messages.error(request, f'Error sending reminder: {str(e)}')
    
    # Get all reviews for this conference that are missing (no decision)
    missing_reviews = Review.objects.filter(
        paper__conference=conference,
        decision__isnull=True
    ).select_related('paper', 'paper__author', 'reviewer')
    
    # Calculate overdue and pending statistics
    from datetime import datetime, timedelta
    today = datetime.now().date()
    
    overdue_count = 0
    pending_count = 0
    affected_reviewers = set()
    affected_papers = set()
    
    for review in missing_reviews:
        affected_reviewers.add(review.reviewer.id)
        affected_papers.add(review.paper.id)
        
        # Calculate if overdue (assuming 30 days from assignment as default deadline)
        if review.submitted_at:
            deadline = review.submitted_at.date() + timedelta(days=30)
            if today > deadline:
                overdue_count += 1
                review.is_overdue = True
                review.days_overdue = (today - deadline).days
            else:
                pending_count += 1
                review.is_overdue = False
                review.days_overdue = 0
                review.days_remaining = (deadline - today).days
        else:
            pending_count += 1
            review.is_overdue = False
            review.days_overdue = 0
            review.deadline = None
    
    nav_items = [
        "Submissions", "Reviews", "Status", "PC", "Events",
        "Email", "Administration", "Conference", "News", "papersetu"
    ]
    active_tab = "Reviews"
    review_dropdown_items = [
        {'label': 'All submissions', 'url': reverse('dashboard:all_submissions', args=[conference.id])},
        {'label': 'Assigned to me', 'url': reverse('dashboard:assigned_to_me', args=[conference.id])},
        {'label': 'Subreviewers', 'url': reverse('dashboard:subreviewers', args=[conference.id])},
        {'label': 'Pool of subreviewers', 'url': reverse('dashboard:pool_subreviewers', args=[conference.id])},
        {'label': 'By PC member', 'url': reverse('dashboard:by_pc_member', args=[conference.id])},
        {'label': 'By submission', 'url': reverse('dashboard:by_submission', args=[conference.id])},
        {'label': 'Delete', 'url': reverse('dashboard:delete_review', args=[conference.id])},
        {'label': 'Send to authors', 'url': reverse('dashboard:send_to_authors', args=[conference.id])},
        {'label': 'Missing reviews', 'url': reverse('dashboard:missing_reviews', args=[conference.id])},
    ]
    return render(request, 'dashboard/missing_reviews.html', {
        'conf_id': conf_id,
        'conference': conference,
        'nav_items': nav_items,
        'active_tab': active_tab,
        'review_dropdown_items': review_dropdown_items,
        'missing_reviews': missing_reviews,
        'overdue_count': overdue_count,
        'pending_count': pending_count,
        'affected_reviewers': len(affected_reviewers),
        'affected_papers': len(affected_papers),
    })

def status_placeholder(request, conf_id):
    conference = get_object_or_404(Conference, id=conf_id)
    nav_items = [
        "Submissions", "Reviews", "Status", "PC", "Events",
        "Email", "Administration", "Conference", "News", "papersetu"
    ]
    active_tab = "Status"
    review_dropdown_items = [
        {'label': 'All submissions', 'url': reverse('dashboard:all_submissions', args=[conference.id])},
        {'label': 'Assigned to me', 'url': reverse('dashboard:assigned_to_me', args=[conference.id])},
        {'label': 'Subreviewers', 'url': reverse('dashboard:subreviewers', args=[conference.id])},
        {'label': 'Pool of subreviewers', 'url': reverse('dashboard:pool_subreviewers', args=[conference.id])},
        {'label': 'By PC member', 'url': reverse('dashboard:by_pc_member', args=[conference.id])},
        {'label': 'By submission', 'url': reverse('dashboard:by_submission', args=[conference.id])},
        {'label': 'Delete', 'url': reverse('dashboard:delete_review', args=[conference.id])},
        {'label': 'Send to authors', 'url': reverse('dashboard:send_to_authors', args=[conference.id])},
        {'label': 'Missing reviews', 'url': reverse('dashboard:missing_reviews', args=[conference.id])},
    ]
    return render(request, 'dashboard/status_placeholder.html', {
        'conference': conference,
        'nav_items': nav_items,
        'active_tab': active_tab,
        'review_dropdown_items': review_dropdown_items,
    })

def events_placeholder(request, conf_id):
    conference = get_object_or_404(Conference, id=conf_id)
    nav_items = [
        "Submissions", "Reviews", "Status", "PC", "Events",
        "Email", "Administration", "Conference", "News", "papersetu"
    ]
    active_tab = "Events"
    review_dropdown_items = [
        {'label': 'All submissions', 'url': reverse('dashboard:all_submissions', args=[conference.id])},
        {'label': 'Assigned to me', 'url': reverse('dashboard:assigned_to_me', args=[conference.id])},
        {'label': 'Subreviewers', 'url': reverse('dashboard:subreviewers', args=[conference.id])},
        {'label': 'Pool of subreviewers', 'url': reverse('dashboard:pool_subreviewers', args=[conference.id])},
        {'label': 'By PC member', 'url': reverse('dashboard:by_pc_member', args=[conference.id])},
        {'label': 'By submission', 'url': reverse('dashboard:by_submission', args=[conference.id])},
        {'label': 'Delete', 'url': reverse('dashboard:delete_review', args=[conference.id])},
        {'label': 'Send to authors', 'url': reverse('dashboard:send_to_authors', args=[conference.id])},
        {'label': 'Missing reviews', 'url': reverse('dashboard:missing_reviews', args=[conference.id])},
    ]
    return render(request, 'dashboard/events_placeholder.html', {
        'conference': conference,
        'nav_items': nav_items,
        'active_tab': active_tab,
        'review_dropdown_items': review_dropdown_items,
    })

@login_required
def email_placeholder(request, conf_id):
    conference = get_object_or_404(Conference, id=conf_id)
    nav_items = [
        "Submissions", "Reviews", "Status", "PC", "Events",
        "Email", "Administration", "Conference", "News", "papersetu"
    ]
    active_tab = "Email"
    review_dropdown_items = [
        {'label': 'All submissions', 'url': reverse('dashboard:all_submissions', args=[conference.id])},
        {'label': 'Assigned to me', 'url': reverse('dashboard:assigned_to_me', args=[conference.id])},
        {'label': 'Subreviewers', 'url': reverse('dashboard:subreviewers', args=[conference.id])},
        {'label': 'Pool of subreviewers', 'url': reverse('dashboard:pool_subreviewers', args=[conference.id])},
        {'label': 'By PC member', 'url': reverse('dashboard:by_pc_member', args=[conference.id])},
        {'label': 'By submission', 'url': reverse('dashboard:by_submission', args=[conference.id])},
        {'label': 'Delete', 'url': reverse('dashboard:delete_review', args=[conference.id])},
        {'label': 'Send to authors', 'url': reverse('dashboard:send_to_authors', args=[conference.id])},
        {'label': 'Missing reviews', 'url': reverse('dashboard:missing_reviews', args=[conference.id])},
    ]
    # Fetch email logs for this conference, only those sent by the chair
    email_logs = PCEmailLog.objects.filter(conference=conference, sender=conference.chair).order_by('-sent_at')[:50]
    return render(request, 'dashboard/email_placeholder.html', {
        'conference': conference,
        'nav_items': nav_items,
        'active_tab': active_tab,
        'review_dropdown_items': review_dropdown_items,
        'email_logs': email_logs,
    })

def news_placeholder(request, conf_id):
    conference = get_object_or_404(Conference, id=conf_id)
    nav_items = [
        "Submissions", "Reviews", "Status", "PC", "Events",
        "Email", "Administration", "Conference", "News", "papersetu"
    ]
    active_tab = "News"
    review_dropdown_items = [
        {'label': 'All submissions', 'url': reverse('dashboard:all_submissions', args=[conference.id])},
        {'label': 'Assigned to me', 'url': reverse('dashboard:assigned_to_me', args=[conference.id])},
        {'label': 'Subreviewers', 'url': reverse('dashboard:subreviewers', args=[conference.id])},
        {'label': 'Pool of subreviewers', 'url': reverse('dashboard:pool_subreviewers', args=[conference.id])},
        {'label': 'By PC member', 'url': reverse('dashboard:by_pc_member', args=[conference.id])},
        {'label': 'By submission', 'url': reverse('dashboard:by_submission', args=[conference.id])},
        {'label': 'Delete', 'url': reverse('dashboard:delete_review', args=[conference.id])},
        {'label': 'Send to authors', 'url': reverse('dashboard:send_to_authors', args=[conference.id])},
        {'label': 'Missing reviews', 'url': reverse('dashboard:missing_reviews', args=[conference.id])},
    ]
    return render(request, 'dashboard/news_placeholder.html', {
        'conference': conference,
        'nav_items': nav_items,
        'active_tab': active_tab,
        'review_dropdown_items': review_dropdown_items,
    })

def papersetu_placeholder(request, conf_id):
    conference = get_object_or_404(Conference, id=conf_id)
    nav_items = [
        "Submissions", "Reviews", "Status", "PC", "Events",
        "Email", "Administration", "Conference", "News", "papersetu"
    ]
    active_tab = "papersetu"
    review_dropdown_items = [
        {'label': 'All submissions', 'url': reverse('dashboard:all_submissions', args=[conference.id])},
        {'label': 'Assigned to me', 'url': reverse('dashboard:assigned_to_me', args=[conference.id])},
        {'label': 'Subreviewers', 'url': reverse('dashboard:subreviewers', args=[conference.id])},
        {'label': 'Pool of subreviewers', 'url': reverse('dashboard:pool_subreviewers', args=[conference.id])},
        {'label': 'By PC member', 'url': reverse('dashboard:by_pc_member', args=[conference.id])},
        {'label': 'By submission', 'url': reverse('dashboard:by_submission', args=[conference.id])},
        {'label': 'Delete', 'url': reverse('dashboard:delete_review', args=[conference.id])},
        {'label': 'Send to authors', 'url': reverse('dashboard:send_to_authors', args=[conference.id])},
        {'label': 'Missing reviews', 'url': reverse('dashboard:missing_reviews', args=[conference.id])},
    ]
    return render(request, 'dashboard/papersetu_placeholder.html', {
        'conference': conference,
        'nav_items': nav_items,
        'active_tab': active_tab,
        'review_dropdown_items': review_dropdown_items,
    })

@login_required
def roles_overview(request):
    # Placeholder: show a simple page for now
    return render(request, 'dashboard/roles_overview.html', {})

@login_required
def my_conferences(request):
    # Get all conferences where the user has a role
    user_roles = UserConferenceRole.objects.filter(user=request.user).select_related('conference')
    conferences = [role.conference for role in user_roles]
    # Also include conferences created by the user that are pending approval (if not already in the list)
    pending_confs = list(Conference.objects.filter(chair=request.user, status='pending'))
    # Merge, avoiding duplicates
    all_confs = {conf.id: conf for conf in conferences}
    for conf in pending_confs:
        all_confs[conf.id] = conf
    return render(request, 'dashboard/my_conferences.html', {'conferences': all_confs.values()})

class CreateConferenceView(LoginRequiredMixin, CreateView):
    model = Conference
    form_class = ConferenceForm
    template_name = 'conference/create_conference.html'
    def get_success_url(self):
        return reverse('dashboard:conference_submissions', args=[self.object.id])
    def form_valid(self, form):
        conference = form.save(commit=False)
        conference.chair = self.request.user
        conference.save()
        return super().form_valid(form)

@login_required
def view_roles(request):
    roles = UserConferenceRole.objects.filter(user=request.user).select_related('conference')
    return render(request, 'dashboard/view_roles.html', {'roles': roles})

@login_required
def publish_with_us(request):
    return render(request, 'dashboard/publish_with_us.html')

@login_required
def manage_cfp(request):
    # Example: Only conferences where user is chair
    chaired_confs = Conference.objects.filter(chair=request.user)
    # Placeholder: CFP form/logic would go here
    return render(request, 'dashboard/manage_cfp.html', {'chaired_confs': chaired_confs})

@login_required
def view_preprints(request):
    # Placeholder: Replace with your actual Preprint model/query
    preprints = []
    return render(request, 'dashboard/view_preprints.html', {'preprints': preprints})

@login_required
def view_slides(request):
    # Placeholder: Replace with your actual Slide model/query
    slides = []
    return render(request, 'dashboard/view_slides.html', {'slides': slides})

@login_required
def read_news(request):
    # Placeholder: Replace with your actual News model/query
    news_items = []
    return render(request, 'dashboard/read_news.html', {'news_items': news_items})

@login_required
def user_settings(request):
    # Placeholder: Add user settings logic here
    return render(request, 'dashboard/settings.html', {'user': request.user})

def read_terms(request):
    return render(request, 'dashboard/read_terms.html')

@login_required
def pc_submissions(request, conf_id):
    conference = get_object_or_404(Conference, id=conf_id)
    user = request.user
    # Only PC members can access
    is_pc_member = UserConferenceRole.objects.filter(user=user, conference=conference, role='pc_member').exists()
    if not is_pc_member:
        return render(request, 'dashboard/forbidden.html', {'message': 'You are not a PC member for this conference.'})
    papers = Paper.objects.filter(conference=conference).select_related('author')
    # For each paper, check if this PC member is assigned as a reviewer
    for paper in papers:
        paper.can_review = paper.reviews.filter(reviewer=user).exists()
        paper.review_id = paper.reviews.filter(reviewer=user).first().id if paper.can_review else None
    context = {
        'conference': conference,
        'papers': papers,
    }
    return render(request, 'dashboard/pc_submissions.html', context)

@login_required
def pc_subreviewers(request, conf_id):
    conference = get_object_or_404(Conference, id=conf_id)
    user = request.user
    # Only PC members can access
    is_pc_member = UserConferenceRole.objects.filter(user=user, conference=conference, role='pc_member').exists()
    if not is_pc_member:
        return render(request, 'dashboard/forbidden.html', {'message': 'You are not a PC member for this conference.'})
    message = None
    message_type = None
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'bulk_invite':
            paper_id = request.POST.get('paper_id')
            bulk_list = request.POST.get('bulk_invitation_list', '').strip().split('\n')
            paper = Paper.objects.get(id=paper_id)
            success_count = 0
            error_count = 0
            error_messages = []
            for line in bulk_list:
                if not line.strip():
                    continue
                # Format: Name <email>
                if '<' in line and '>' in line:
                    name = line.split('<')[0].strip()
                    email = line.split('<')[1].split('>')[0].strip()
                else:
                    error_messages.append(f'Invalid format: {line}')
                    error_count += 1
                    continue
                try:
                    subreviewer = User.objects.filter(email=email).first()
                    if not subreviewer:
                        error_messages.append(f'User not found: {email}')
                        error_count += 1
                        continue
                    # Check for duplicate invite
                    if SubreviewerInvite.objects.filter(paper=paper, subreviewer=subreviewer).exists():
                        error_messages.append(f'Already invited: {email}')
                        error_count += 1
                        continue
                    token = get_random_string(48)
                    invite = SubreviewerInvite.objects.create(
                        paper=paper,
                        subreviewer=subreviewer,
                        invited_by=user,
                        email=email,
                        token=token
                    )
                    UserConferenceRole.objects.get_or_create(user=subreviewer, conference=conference, role='subreviewer')
                    subject = f"Paper Review Assignment: '{paper.title}'"
                    message_body = f"Dear {name},\n\nYou have been assigned a paper for review (\"{paper.title}\") in the conference '{conference.name}'. Please log in to your dashboard to accept or reject the request.\n\nBest regards,\n{request.user.get_full_name() or request.user.username}\nConference Chair"
                    send_mail(subject, message_body, None, [email])
                    success_count += 1
                except Exception as e:
                    error_messages.append(f'Error for {email}: {str(e)}')
                    error_count += 1
            message = f"Bulk invitation complete. {success_count} sent, {error_count} errors."
            if error_messages:
                message += '\n' + '\n'.join(error_messages[:5])
                if len(error_messages) > 5:
                    message += f'\n... and {len(error_messages) - 5} more errors.'
            message_type = 'success' if success_count > 0 else 'error'
        elif action == 'invite':
            paper_id = request.POST.get('paper_id')
            user_id = request.POST.get('user_id')
            email = request.POST.get('email')
            if paper_id and user_id and email:
                paper = Paper.objects.get(id=paper_id)
                subreviewer = User.objects.get(id=user_id)
                token = get_random_string(48)
                invite = SubreviewerInvite.objects.create(
                    paper=paper,
                    subreviewer=subreviewer,
                    invited_by=user,
                    email=email,
                    token=token
                )
                UserConferenceRole.objects.get_or_create(user=subreviewer, conference=conference, role='subreviewer')
                body = f"Dear {subreviewer.get_full_name() or subreviewer.username},\n\nYou have been assigned a paper for review (\"{paper.title}\") in the conference '{conference.name}'. Please log in to your dashboard to accept or reject the request.\n\nBest regards,\n{user.get_full_name() or user.username}\nPC Member"
                send_mail(
                    subject=f"Paper Review Assignment: '{paper.title}'",
                    message=body,
                    from_email=None,
                    recipient_list=[email],
                )
                message = f"Assignment email sent to {subreviewer.get_full_name() or subreviewer.username} for paper '{paper.title}'."
                message_type = 'success'
            else:
                message = "Please select a paper, subreviewer, and provide an email."
                message_type = 'error'
    # Only show invites sent by this PC member
    invites = SubreviewerInvite.objects.filter(paper__conference=conference, invited_by=user).select_related('paper', 'subreviewer')
    papers = Paper.objects.filter(conference=conference)
    all_users = User.objects.exclude(id=conference.chair.id)
    context = {
        'conference': conference,
        'papers': papers,
        'all_users': all_users,
        'invites': invites,
        'message': message,
        'message_type': message_type,
    }
    return render(request, 'dashboard/pc_subreviewers.html', context)

@login_required
def delete_submissions(request, conf_id):
    conference = Conference.objects.get(id=conf_id)
    if conference.chair != request.user:
        return render(request, 'dashboard/forbidden.html', {'message': 'Only the conference chair can access this feature.'})
    
    # Get all papers for this conference
    papers = Paper.objects.filter(conference=conference).select_related('author')
    
    # Create a map to group authors by email
    author_map = {}
    
    # Add main authors from Paper.author
    for paper in papers:
        main_author = paper.author
        email = main_author.email
        name = f"{main_author.first_name} {main_author.last_name}" if main_author.first_name and main_author.last_name else main_author.username
        
        if email not in author_map:
            author_map[email] = {
                'name': name,
                'email': email,
                'country': getattr(main_author, 'country_region', 'N/A'),
                'affiliation': getattr(main_author, 'affiliation', 'N/A'),
                'papers': []
            }
        author_map[email]['papers'].append(paper)
    
    # Add additional authors from Author model
    additional_authors = Author.objects.filter(paper__conference=conference).select_related('paper')
    for author in additional_authors:
        email = author.email
        name = f"{author.first_name} {author.last_name}"
        
        if email not in author_map:
            author_map[email] = {
                'name': name,
                'email': email,
                'country': author.country_region,
                'affiliation': author.affiliation,
                'papers': []
            }
        author_map[email]['papers'].append(author.paper)
    
    # Convert to list and add submission count
    author_list = []
    for email, data in author_map.items():
        # Remove duplicate papers
        unique_papers = list(set(data['papers']))
        author_list.append({
            'name': data['name'],
            'email': email,
            'country': data['country'],
            'affiliation': data['affiliation'],
            'papers': unique_papers,
            'submission_count': len(unique_papers),
        })
    
    if request.method == 'POST':
        selected_emails = request.POST.getlist('selected_authors')
        # Delete all papers by these authors for this conference
        for email in selected_emails:
            # Delete papers where main author matches
            Paper.objects.filter(conference=conference, author__email=email).delete()
            # Delete papers where additional author matches
            author_papers = Author.objects.filter(email=email, paper__conference=conference).values_list('paper_id', flat=True)
            Paper.objects.filter(id__in=author_papers, conference=conference).delete()
        return redirect('dashboard:delete_submissions', conf_id=conf_id)
    
    return render(request, 'dashboard/delete_submissions.html', {
        'conference': conference,
        'author_list': author_list,
    })

@login_required
def authors_list(request, conf_id):
    conference = Conference.objects.get(id=conf_id)
    if conference.chair != request.user:
        return render(request, 'dashboard/forbidden.html', {'message': 'Only the conference chair can access this feature.'})
    
    # Get all papers for this conference
    papers = Paper.objects.filter(conference=conference).select_related('author')
    
    # Create a map to group authors by email
    author_map = {}
    
    # Add main authors from Paper.author
    for paper in papers:
        main_author = paper.author
        email = main_author.email
        name = f"{main_author.first_name} {main_author.last_name}" if main_author.first_name and main_author.last_name else main_author.username
        
        if email not in author_map:
            author_map[email] = {
                'name': name,
                'email': email,
                'country': getattr(main_author, 'country_region', 'N/A'),
                'affiliation': getattr(main_author, 'affiliation', 'N/A'),
                'papers': []
            }
        author_map[email]['papers'].append(paper)
    
    # Add additional authors from Author model
    additional_authors = Author.objects.filter(paper__conference=conference).select_related('paper')
    for author in additional_authors:
        email = author.email
        name = f"{author.first_name} {author.last_name}"
        
        if email not in author_map:
            author_map[email] = {
                'name': name,
                'email': email,
                'country': author.country_region,
                'affiliation': author.affiliation,
                'papers': []
            }
        author_map[email]['papers'].append(author.paper)
    
    # Convert to list and add submission count
    author_list = []
    for email, data in author_map.items():
        # Remove duplicate papers
        unique_papers = list(set(data['papers']))
        author_list.append({
            'name': data['name'],
            'email': email,
            'country': data['country'],
            'affiliation': data['affiliation'],
            'papers': unique_papers,
            'submission_count': len(unique_papers),
        })
    
    return render(request, 'dashboard/authors_list.html', {
        'conference': conference,
        'author_list': author_list,
    })

@login_required
def authors_list_table(request, conf_id):
    conference = Conference.objects.get(id=conf_id)
    if conference.chair != request.user:
        return render(request, 'dashboard/forbidden.html', {'message': 'Only the conference chair can access this feature.'})
    
    search = request.GET.get('search', '').strip().lower()
    
    # Get all papers for this conference
    papers = Paper.objects.filter(conference=conference).select_related('author')
    
    # Create a map to group authors by email
    author_map = {}
    
    # Add main authors from Paper.author
    for paper in papers:
        main_author = paper.author
        email = main_author.email
        name = f"{main_author.first_name} {main_author.last_name}" if main_author.first_name and main_author.last_name else main_author.username
        
        if email not in author_map:
            author_map[email] = {
                'name': name,
                'email': email,
                'country': getattr(main_author, 'country_region', 'N/A'),
                'affiliation': getattr(main_author, 'affiliation', 'N/A'),
                'papers': []
            }
        author_map[email]['papers'].append(paper)
    
    # Add additional authors from Author model
    additional_authors = Author.objects.filter(paper__conference=conference).select_related('paper')
    for author in additional_authors:
        email = author.email
        name = f"{author.first_name} {author.last_name}"
        
        if email not in author_map:
            author_map[email] = {
                'name': name,
                'email': email,
                'country': author.country_region,
                'affiliation': author.affiliation,
                'papers': []
            }
        author_map[email]['papers'].append(author.paper)
    
    # Convert to list, filter by search, and add submission count
    author_list = []
    for email, data in author_map.items():
        # Filter by search
        if search and search not in data['name'].lower() and search not in email.lower():
            continue
            
        # Remove duplicate papers
        unique_papers = list(set(data['papers']))
        author_list.append({
            'name': data['name'],
            'email': email,
            'country': data['country'],
            'affiliation': data['affiliation'],
            'papers': unique_papers,
            'submission_count': len(unique_papers),
        })
    
    return render(request, 'dashboard/partials/authors_table_body.html', {'author_list': author_list})

@login_required
def delete_submissions_table(request, conf_id):
    conference = Conference.objects.get(id=conf_id)
    if conference.chair != request.user:
        return render(request, 'dashboard/forbidden.html', {'message': 'Only the conference chair can access this feature.'})
    
    search = request.GET.get('search', '').strip().lower()
    
    # Get all papers for this conference
    papers = Paper.objects.filter(conference=conference).select_related('author')
    
    # Create a map to group authors by email
    author_map = {}
    
    # Add main authors from Paper.author
    for paper in papers:
        main_author = paper.author
        email = main_author.email
        name = f"{main_author.first_name} {main_author.last_name}" if main_author.first_name and main_author.last_name else main_author.username
        
        if email not in author_map:
            author_map[email] = {
                'name': name,
                'email': email,
                'country': getattr(main_author, 'country_region', 'N/A'),
                'affiliation': getattr(main_author, 'affiliation', 'N/A'),
                'papers': []
            }
        author_map[email]['papers'].append(paper)
    
    # Add additional authors from Author model
    additional_authors = Author.objects.filter(paper__conference=conference).select_related('paper')
    for author in additional_authors:
        email = author.email
        name = f"{author.first_name} {author.last_name}"
        
        if email not in author_map:
            author_map[email] = {
                'name': name,
                'email': email,
                'country': author.country_region,
                'affiliation': author.affiliation,
                'papers': []
            }
        author_map[email]['papers'].append(author.paper)
    
    # Convert to list, filter by search, and add submission count
    author_list = []
    for email, data in author_map.items():
        # Filter by search
        if search and search not in data['name'].lower() and search not in email.lower():
            continue
            
        # Remove duplicate papers
        unique_papers = list(set(data['papers']))
        author_list.append({
            'name': data['name'],
            'email': email,
            'country': data['country'],
            'affiliation': data['affiliation'],
            'papers': unique_papers,
            'submission_count': len(unique_papers),
        })
    
    return render(request, 'dashboard/partials/delete_submissions_table_body.html', {'author_list': author_list})

@login_required
def download_submissions(request, conf_id):
    conference = Conference.objects.get(id=conf_id)
    papers = Paper.objects.filter(conference=conference)
    # Create a zip in memory
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for paper in papers:
            if paper.file:
                filename = f"{slugify(paper.title)}_{paper.id}{os.path.splitext(paper.file.name)[-1]}"
                file_path = paper.file.path
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        zip_file.writestr(filename, f.read())
    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{slugify(conference.name)}_submissions.zip"'
    return response

@login_required
def view_paper_submission(request, conf_id, submission_id):
    """
    View detailed information about a specific paper submission.
    Only accessible by the conference chair.
    """
    conference = get_object_or_404(Conference, id=conf_id)
    paper = get_object_or_404(Paper, id=submission_id, conference=conference)
    
    # Ensure only the chair can access
    if conference.chair != request.user:
        return render(request, 'dashboard/forbidden.html', {
            'message': 'Only the conference chair can view paper details.'
        })
    
    # Get all authors for this paper (main author + additional authors)
    authors = []
    
    # Add main author
    main_author = paper.author
    authors.append({
        'first_name': main_author.first_name or '',
        'last_name': main_author.last_name or '',
        'email': main_author.email,
        'country': getattr(main_author, 'country_region', 'N/A'),
        'affiliation': getattr(main_author, 'affiliation', 'N/A'),
        'web_page': getattr(main_author, 'web_page', ''),
        'is_corresponding': True,  # Main author is typically corresponding
    })
    
    # Add additional authors from Author model
    additional_authors = Author.objects.filter(paper=paper)
    for author in additional_authors:
        authors.append({
            'first_name': author.first_name,
            'last_name': author.last_name,
            'email': author.email,
            'country': author.country_region,
            'affiliation': author.affiliation,
            'web_page': author.web_page,
            'is_corresponding': author.is_corresponding,
        })
    
    # Get reviews for this paper
    reviews = Review.objects.filter(paper=paper).select_related('reviewer')
    review_stats = {
        'total': reviews.count(),
        'accepted': reviews.filter(decision='accept').count(),
        'rejected': reviews.filter(decision='reject').count(),
        'pending': reviews.filter(decision__isnull=True).count(),
    }
    
    # Get subreviewer invites for this paper
    subreviewer_invites = SubreviewerInvite.objects.filter(paper=paper).select_related('subreviewer', 'invited_by')
    
    # Get assigned reviewers (PC members who have been assigned to review this paper)
    assigned_reviewers = []
    for review in reviews:
        assigned_reviewers.append({
            'name': review.reviewer.get_full_name() or review.reviewer.username,
            'email': review.reviewer.email,
            'status': 'Done' if review.decision else 'Not Done',
            'decision': review.decision,
            'submitted_at': review.submitted_at,
        })
    
    # Navigation items for the conference
    nav_items = [
        "Submissions", "Reviews", "Status", "PC", "Events",
        "Email", "Administration", "Conference", "News", "papersetu"
    ]
    
    context = {
        'conference': conference,
        'paper': paper,
        'authors': authors,
        'reviews': reviews,
        'review_stats': review_stats,
        'assigned_reviewers': assigned_reviewers,
        'subreviewer_invites': subreviewer_invites,
        'nav_items': nav_items,
        'active_tab': 'Submissions',
    }
    
    return render(request, 'dashboard/view_paper_submission.html', context)

@login_required
def manage_submission(request, conf_id, submission_id):
    """Manage a single submission - chair and PC members only"""
    conference = get_object_or_404(Conference, id=conf_id)
    paper = get_object_or_404(Paper, id=submission_id, conference=conference)
    
    # Check if user has permission to manage this paper (chair or PC member only)
    user_roles = UserConferenceRole.objects.filter(user=request.user, conference=conference).values_list('role', flat=True)
    is_chair = conference.chair == request.user
    is_pc_member = 'pc_member' in user_roles
    
    if not (is_chair or is_pc_member):
        return render(request, 'dashboard/forbidden.html', {'conference': conference})
    
    # Get all authors (main author + additional authors)
    main_author = paper.author
    additional_authors = paper.authors.all()
    
    # Always fetch the latest reviews for this paper
    reviews = paper.reviews.exclude(decision='reject').select_related('reviewer').order_by('-submitted_at')
    
    # Get subreviewers for this paper
    subreviewers = User.objects.filter(
        subreviewer_invites__paper=paper,
        subreviewer_invites__status='accepted'
    ).distinct()
    
    # Get review statistics
    total_reviews = reviews.filter(decision__in=['accept', 'reject']).count()
    accept_count = reviews.filter(decision='accept').count()
    reject_count = reviews.filter(decision='reject').count()
    pending_reviews = reviews.filter(decision__isnull=True).count()
    
    # Count subreviewer recommendations
    subreviewer_recommendations = reviews.filter(recommendation__isnull=False, decision__isnull=True).count()
    accept_recommendations = reviews.filter(recommendation='accept', decision__isnull=True).count()
    reject_recommendations = reviews.filter(recommendation='reject', decision__isnull=True).count()
    
    # Prepare keywords list for template
    keywords_list = [k.strip() for k in paper.keywords.split(',')] if paper.keywords else []
    
    # Handle decision submission
    if request.method == 'POST':
        # Plagiarism percentage update
        if is_chair and 'update_plagiarism' in request.POST:
            try:
                plagiarism_percentage = int(request.POST.get('plagiarism_percentage', '').strip())
                if 0 <= plagiarism_percentage <= 100:
                    paper.plagiarism_percentage = plagiarism_percentage
                    paper.save()
                    messages.success(request, 'Plagiarism percentage updated successfully.')
                else:
                    messages.error(request, 'Plagiarism percentage must be between 0 and 100.')
            except (ValueError, TypeError):
                messages.error(request, 'Invalid plagiarism percentage value.')
            return redirect('dashboard:manage_submission', conf_id=conf_id, submission_id=submission_id)
        # Decision update
        decision = request.POST.get('decision')
        if decision in ['accept', 'reject'] and is_chair:  # Only chair can make final decisions
            old_status = paper.status
            # Map to model status values
            if decision == 'accept':
                paper.status = 'accepted'
            elif decision == 'reject':
                paper.status = 'rejected'
            paper.save()
            # Create notification for author
            Notification.objects.create(
                recipient=paper.author,
                notification_type='paper_decision',
                title=f'Paper Decision - {decision.title()}',
                message=f'Your paper "{paper.title}" has been {decision}ed for {conference.name}.',
                related_paper=paper,
                related_conference=conference
            )
            # Always send email to author when final decision is set/changed
            corresponding_author = paper.authors.filter(is_corresponding=True).first()
            if not corresponding_author:
                corresponding_author = paper.author
            subject = f"Paper Decision for '{paper.title}' - {conference.name}"
            if decision == 'accept':
                body = f"Dear {corresponding_author.first_name if hasattr(corresponding_author, 'first_name') else corresponding_author.get_full_name()},\n\n"
                body += f"We are pleased to inform you that your paper '{paper.title}' has been ACCEPTED.\n\n"
            else:
                body = f"Dear {corresponding_author.first_name if hasattr(corresponding_author, 'first_name') else corresponding_author.get_full_name()},\n\n"
                body += f"We regret to inform you that your paper '{paper.title}' has been REJECTED.\n\n"
            body += f"Best regards,\n{conference.name} Program Committee"
            to_email = corresponding_author.email if hasattr(corresponding_author, 'email') else corresponding_author.email
            try:
                send_mail(subject, body, None, [to_email])
            except Exception as e:
                print(f"[ERROR] Failed to send decision email to {to_email}: {e}")
            messages.success(request, f'Paper has been {decision}ed successfully.')
            # Always redirect to manage_submission to see updated data
            return redirect('dashboard:manage_submission', conf_id=conf_id, submission_id=submission_id)
    
    context = {
        'conference': conference,
        'paper': paper,
        'main_author': main_author,
        'additional_authors': additional_authors,
        'reviews': reviews,
        'subreviewers': subreviewers,
        'total_reviews': total_reviews,
        'accept_count': accept_count,
        'reject_count': reject_count,
        'pending_reviews': pending_reviews,
        'subreviewer_recommendations': subreviewer_recommendations,
        'accept_recommendations': accept_recommendations,
        'reject_recommendations': reject_recommendations,
        'is_chair': is_chair,
        'is_pc_member': is_pc_member,
        'keywords_list': keywords_list,
    }
    
    return render(request, 'dashboard/manage_submission.html', context)

@login_required
def authors_manage(request, conf_id):
    """Manage author communications page"""
    conference = get_object_or_404(Conference, id=conf_id)
    
    # Check if user has permission to access this page (chair or PC member)
    user_roles = UserConferenceRole.objects.filter(user=request.user, conference=conference).values_list('role', flat=True)
    is_chair = conference.chair == request.user
    is_pc_member = 'pc_member' in user_roles
    
    if not (is_chair or is_pc_member):
        return render(request, 'dashboard/forbidden.html', {'conference': conference})
    
    context = {
        'conference': conference,
        'is_chair': is_chair,
        'is_pc_member': is_pc_member,
    }
    
    return render(request, 'dashboard/authors.html', context)

@login_required
def change_review_decision(request, conf_id, submission_id, review_id):
    """Change review marks/comments for a specific review (no final decision here)."""
    conference = get_object_or_404(Conference, id=conf_id)
    paper = get_object_or_404(Paper, id=submission_id, conference=conference)
    review = get_object_or_404(Review, id=review_id, paper=paper)
    # Check if user has permission to change this review
    if not (conference.chair == request.user or \
            UserConferenceRole.objects.filter(user=request.user, conference=conference, role='pc_member').exists()):
        return render(request, 'dashboard/forbidden.html', {'message': 'You do not have permission to change review decisions.'})
    if request.method == 'POST':
        # Only allow updating marks (rating), comments, and remarks
        marks = request.POST.get('marks')
        comments = request.POST.get('comments', '')
        remarks = request.POST.get('remarks', '')
        confidence = request.POST.get('confidence')
        # Update marks (rating)
        if marks is not None and marks != '':
            review.rating = int(marks)
        else:
            review.rating = None
        # Update confidence if present
        if confidence is not None and confidence != '':
            review.confidence = int(confidence)
        else:
            review.confidence = None
        review.comments = comments
        review.remarks = remarks
        review.save()
        messages.success(request, 'Review updated successfully!')
        return redirect('dashboard:manage_submission', conf_id=conf_id, submission_id=submission_id)
    context = {
        'conference': conference,
        'paper': paper,
        'review': review,
    }
    return render(request, 'dashboard/change_review_decision.html', context)

@login_required
@require_POST
def approve_recommendation(request, review_id):
    """Approve a subreviewer recommendation and set it as the final decision, and email the corresponding author if accepted. If rejected, set paper status to pending and do not email author."""
    import json
    from django.http import JsonResponse
    review = get_object_or_404(Review, id=review_id)
    conference = review.paper.conference
    paper = review.paper
    # Only chair can approve recommendations
    if conference.chair != request.user:
        if request.content_type == 'application/json' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Only the conference chair can approve recommendations.'})
        else:
            return redirect('dashboard:conference_submissions', conf_id=conference.id)
    try:
        # Accept both AJAX and form POSTs
        if request.content_type == 'application/json' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
            data = json.loads(request.body)
            decision = data.get('decision')
        else:
            decision = request.POST.get('decision')
        if decision not in ['accept', 'reject']:
            if request.content_type == 'application/json' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Invalid decision value.'})
            else:
                return redirect('dashboard:conference_submissions', conf_id=conference.id)
        # Set the recommendation as the final decision
        review.decision = decision
        review.save()
        # Update the paper status and handle email logic
        if decision == 'accept':
            paper.status = 'accepted'
            paper.save()
            # Send notification to the subreviewer
            Notification.objects.create(
                recipient=review.reviewer,
                notification_type='paper_review',
                title=f'Your Review Recommendation Approved',
                message=f'Your {decision} recommendation for paper "{review.paper.title}" has been approved by the conference chair.',
                related_paper=review.paper,
                related_conference=conference
            )
            # Find corresponding author
            corresponding_author = paper.authors.filter(is_corresponding=True).first()
            if not corresponding_author:
                # fallback to main author
                corresponding_author = paper.author
            # Compose email
            subject = f"Paper Decision for '{paper.title}' - {conference.name}"
            body = f"Dear {corresponding_author.first_name if hasattr(corresponding_author, 'first_name') else corresponding_author.get_full_name()},\n\n"
            body += f"We are pleased to inform you that your paper '{paper.title}' has been ACCEPTED.\n\n"
            body += f"Marks: {review.rating}\nComments: {review.comments}\n\n"
            body += "This decision is based on the subreviewer's recommendation, as approved by the conference chair.\n\n"
            body += f"Best regards,\n{conference.name} Program Committee"
            to_email = corresponding_author.email if hasattr(corresponding_author, 'email') else corresponding_author.email
            send_mail(subject, body, None, [to_email])
        elif decision == 'reject':
            # Set paper status to 'pending' (not rejected), do not email author
            paper.status = 'pending'
            paper.save()
            # Send notification to the subreviewer
            Notification.objects.create(
                recipient=review.reviewer,
                notification_type='paper_review',
                title=f'Your Review Recommendation Rejected',
                message=f'Your reject recommendation for paper "{review.paper.title}" has been rejected by the conference chair. The final decision will be made separately.',
                related_paper=review.paper,
                related_conference=conference
            )
            # Send real email to subreviewer
            subject = f"Your Review Has Been Rejected - {conference.name}"
            body = f"Dear {review.reviewer.get_full_name() or review.reviewer.username},\n\nYour review for the paper '{paper.title}' has been rejected by the chair of {conference.name}. The final decision will be made separately.\n\nBest regards,\n{conference.name} Program Committee"
            to_email = review.reviewer.email
            send_mail(subject, body, None, [to_email])
        # Redirect to referring page or submissions page
        if request.content_type == 'application/json' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': f'Recommendation processed as {decision}.'})
        else:
            next_url = request.META.get('HTTP_REFERER')
            if next_url:
                return redirect(next_url)
            return redirect('dashboard:conference_submissions', conf_id=conference.id)
    except json.JSONDecodeError:
        if request.content_type == 'application/json' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Invalid JSON data.'})
        else:
            return redirect('dashboard:conference_submissions', conf_id=conference.id)
    except Exception as e:
        if request.content_type == 'application/json' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': str(e)})
        else:
            return redirect('dashboard:conference_submissions', conf_id=conference.id)

@login_required
def add_review(request, conf_id, submission_id):
    conference = get_object_or_404(Conference, id=conf_id)
    paper = get_object_or_404(Paper, id=submission_id, conference=conference)
    user_review = Review.objects.filter(paper=paper, reviewer=request.user).first()
    is_chair = conference.chair == request.user
    if not user_review:
        messages.error(request, 'You are not assigned to review this paper.')
        return redirect('dashboard:all_submissions', conf_id=conf_id)
    if request.method == 'POST':
        marks = request.POST.get('marks')
        confidence = request.POST.get('confidence')
        comments = request.POST.get('comments', '')
        remarks = request.POST.get('remarks', '')
        if marks is not None and marks != '':
            user_review.rating = int(marks)
        else:
            user_review.rating = None
        if confidence is not None and confidence != '':
            user_review.confidence = int(confidence)
        else:
            user_review.confidence = None
        user_review.comments = comments
        user_review.remarks = remarks
        user_review.save()
        messages.success(request, 'Review submitted successfully!')
        return redirect('dashboard:all_submissions', conf_id=conf_id)
    context = {
        'conference': conference,
        'paper': paper,
        'review': user_review,
        'is_chair': is_chair,
    }
    return render(request, 'dashboard/add_review.html', context)

@login_required
def update_review(request, conf_id, submission_id):
    conference = get_object_or_404(Conference, id=conf_id)
    paper = get_object_or_404(Paper, id=submission_id, conference=conference)
    user_review = Review.objects.filter(paper=paper, reviewer=request.user).first()
    is_chair = conference.chair == request.user
    if not user_review:
        messages.error(request, 'You do not have a review for this paper.')
        return redirect('dashboard:all_submissions', conf_id=conf_id)
    if request.method == 'POST':
        marks = request.POST.get('marks')
        confidence = request.POST.get('confidence')
        comments = request.POST.get('comments', '')
        remarks = request.POST.get('remarks', '')
        if marks is not None and marks != '':
            user_review.rating = int(marks)
        else:
            user_review.rating = None
        if confidence is not None and confidence != '':
            user_review.confidence = int(confidence)
        else:
            user_review.confidence = None
        user_review.comments = comments
        user_review.remarks = remarks
        user_review.save()
        messages.success(request, 'Review updated successfully!')
        return redirect('dashboard:all_submissions', conf_id=conf_id)
    context = {
        'conference': conference,
        'paper': paper,
        'review': user_review,
        'is_chair': is_chair,
    }
    return render(request, 'dashboard/update_review.html', context)

@login_required
def contact_subreviewer(request, conf_id, submission_id, subreviewer_id):
    """Contact a subreviewer for a submission"""
    conference = get_object_or_404(Conference, id=conf_id)
    paper = get_object_or_404(Paper, id=submission_id, conference=conference)
    subreviewer = get_object_or_404(User, id=subreviewer_id)
    
    # Check if user is assigned to review this paper
    user_review = Review.objects.filter(paper=paper, reviewer=request.user).first()
    if not user_review:
        messages.error(request, 'You are not assigned to review this paper.')
        return redirect('dashboard:all_submissions', conf_id=conf_id)
    
    # Check if subreviewer is assigned to this paper
    subreviewer_invite = SubreviewerInvite.objects.filter(
        paper=paper, 
        subreviewer=subreviewer
    ).first()
    
    if not subreviewer_invite:
        messages.error(request, 'This subreviewer is not assigned to this paper.')
        return redirect('dashboard:all_submissions', conf_id=conf_id)
    
    if request.method == 'POST':
        subject = request.POST.get('subject')
        message_text = request.POST.get('message')
        
        if subject and message_text:
            # Send email to subreviewer
            from django.core.mail import send_mail
            send_mail(
                subject=subject,
                message=message_text,
                from_email=request.user.email,
                recipient_list=[subreviewer.email],
            )
            messages.success(request, f'Email sent to {subreviewer.get_full_name() or subreviewer.username}')
            return redirect('dashboard:all_submissions', conf_id=conf_id)
        else:
            messages.error(request, 'Please provide both subject and message.')
    
    context = {
        'conference': conference,
        'paper': paper,
        'subreviewer': subreviewer,
        'subreviewer_invite': subreviewer_invite,
    }
    return render(request, 'dashboard/contact_subreviewer.html', context)

@login_required
def view_submission_details(request, conf_id, submission_id):
    """View detailed information about a submission"""
    conference = get_object_or_404(Conference, id=conf_id)
    paper = get_object_or_404(Paper, id=submission_id, conference=conference)
    user_review = Review.objects.filter(paper=paper, reviewer=request.user).first()
    # Determine if the user is the chair
    is_chair = conference.chair == request.user

    # Handle plagiarism percentage update by chair
    if request.method == 'POST' and is_chair and 'update_plagiarism' in request.POST:
        try:
            plagiarism_percentage = int(request.POST.get('plagiarism_percentage', '').strip())
            if 0 <= plagiarism_percentage <= 100:
                paper.plagiarism_percentage = plagiarism_percentage
                paper.save()
                messages.success(request, 'Plagiarism percentage updated successfully.')
            else:
                messages.error(request, 'Plagiarism percentage must be between 0 and 100.')
        except (ValueError, TypeError):
            messages.error(request, 'Invalid plagiarism percentage value.')
        return redirect('dashboard:view_submission_details', conf_id=conf_id, submission_id=submission_id)

    # Get all reviews for this paper
    reviews = paper.reviews.all().select_related('reviewer')
    # Get subreviewer invites
    subreviewer_invites = paper.subreviewer_invites.all().select_related('subreviewer', 'invited_by')
    context = {
        'conference': conference,
        'paper': paper,
        'user_review': user_review,
        'reviews': reviews,
        'subreviewer_invites': subreviewer_invites,
        'is_chair': is_chair,
    }
    return render(request, 'dashboard/view_submission_details.html', context)

class AdminFeatureBaseView(LoginRequiredMixin, View):
    feature_key = None  # e.g., 'config', 'registration', etc.
    template_name = None

    def get(self, request, conf_id):
        conference = get_object_or_404(Conference, id=conf_id)
        toggle = ConferenceFeatureToggle.objects.filter(conference=conference, feature=self.feature_key).first()
        enabled = toggle.enabled if toggle else False
        context = {
            'conference': conference,
            'feature_enabled': enabled,
            'feature_name': dict(FEATURE_CHOICES).get(self.feature_key, self.feature_key.title()),
        }
        if not enabled:
            context['disabled_message'] = f"{context['feature_name']} is not enabled for this conference."
        return render(request, self.template_name, context)

# Feature views
class ConfigFeatureView(AdminFeatureBaseView):
    feature_key = 'config'
    template_name = 'dashboard/admin_features/config.html'

class RegistrationFeatureView(AdminFeatureBaseView):
    feature_key = 'registration'
    template_name = 'dashboard/admin_features/registration.html'

class UtilitiesFeatureView(AdminFeatureBaseView):
    feature_key = 'utilities'
    template_name = 'dashboard/admin_features/utilities.html'

class AnalyticsFeatureView(AdminFeatureBaseView):
    feature_key = 'analytics'
    template_name = 'dashboard/admin_features/analytics.html'

class StatisticsFeatureView(AdminFeatureBaseView):
    feature_key = 'statistics'
    template_name = 'dashboard/admin_features/statistics.html'

class DemoFeatureView(AdminFeatureBaseView):
    feature_key = 'demo'
    template_name = 'dashboard/admin_features/demo.html'

class TracksFeatureView(AdminFeatureBaseView):
    feature_key = 'tracks'
    template_name = 'dashboard/admin_features/tracks.html'

class CFPFeatureView(AdminFeatureBaseView):
    feature_key = 'cfp'
    template_name = 'dashboard/admin_features/cfp.html'

class ProgramFeatureView(AdminFeatureBaseView):
    feature_key = 'program'
    template_name = 'dashboard/admin_features/program.html'

class ProceedingsFeatureView(AdminFeatureBaseView):
    feature_key = 'proceedings'
    template_name = 'dashboard/admin_features/proceedings.html'

@login_required
def export_submissions_excel(request, conf_id):
    """
    Export all submissions for a conference as an Excel (.xlsx) file with selected columns.
    Columns are selected by the chair via POST.
    """
    from django.http import HttpResponse
    conference = get_object_or_404(Conference, id=conf_id)
    user = request.user
    if conference.chair != user:
        return render(request, 'dashboard/forbidden.html', {
            'message': 'Only the conference chair can export submissions.'
        })
    if request.method != 'POST':
        return redirect('dashboard:export_submissions_excel_options', conf_id=conf_id)
    # Get selected columns from POST
    selected_columns = request.POST.getlist('columns')
    # Map keys to Paper model fields or computed values
    column_map = {
        'authors': lambda paper: paper.author.get_full_name() or paper.author.username or str(paper.author),
        'title': lambda paper: paper.title,
        'paper_id': lambda paper: paper.id,
        'time': lambda paper: paper.submitted_at.strftime('%Y-%m-%d %H:%M') if hasattr(paper, 'submitted_at') and paper.submitted_at else '',
        'decision': lambda paper: getattr(paper, 'status', ''),
        'keywords': lambda paper: getattr(paper, 'keywords', ''),
        'abstract': lambda paper: getattr(paper, 'abstract', ''),
    }
    # Prepare workbook
    papers = Paper.objects.filter(conference=conference).select_related('author').order_by('id')
    wb = Workbook()
    ws = wb.active
    ws.title = 'Submissions'
    # Header
    ws.append([col.capitalize() if col != 'paper_id' else 'Paper ID' for col in selected_columns])
    for paper in papers:
        ws.append([smart_str(column_map[col](paper)) for col in selected_columns])
    # Prepare response
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{conference.acronym}_submissions.xlsx"'
    wb.save(response)
    return response

@login_required
def export_submissions_excel_options(request, conf_id):
    """
    Render a page for the chair to select which columns to include in the Excel export.
    """
    conference = get_object_or_404(Conference, id=conf_id)
    user = request.user
    if conference.chair != user:
        return render(request, 'dashboard/forbidden.html', {
            'message': 'Only the conference chair can export submissions.'
        })
    # Define available columns (could be made dynamic if needed)
    available_columns = [
        {'key': 'authors', 'label': 'Authors', 'default': True},
        {'key': 'title', 'label': 'Title', 'default': True},
        {'key': 'paper_id', 'label': 'Paper ID', 'default': True},
        {'key': 'time', 'label': 'Time', 'default': False},
        {'key': 'decision', 'label': 'Decision', 'default': False},
        {'key': 'keywords', 'label': 'Keywords', 'default': False},
        {'key': 'abstract', 'label': 'Abstract', 'default': False},
    ]
    return render(request, 'dashboard/export_submissions_excel_options.html', {
        'conference': conference,
        'available_columns': available_columns,
    })
