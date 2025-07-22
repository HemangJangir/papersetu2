from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import ConferenceForm, ReviewerVolunteerForm, PaperSubmissionForm
from .models import Conference, ReviewerPool, ReviewInvite, UserConferenceRole, Paper, Review
from accounts.models import User
from django.utils.crypto import get_random_string
from django.http import Http404, FileResponse
import os
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django import forms
from conference.models import Review
from django.core.mail import EmailMessage
from django.conf import settings
from .models import Author

import stripe
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
from .models import Paper
from django.db import models

stripe.api_key = settings.STRIPE_SECRET_KEY

@csrf_exempt
def create_checkout_session(request, paper_id):
    paper = get_object_or_404(Paper, id=paper_id)
    if paper.is_paid or paper.status != 'accepted':
        return JsonResponse({'error': 'Payment not allowed.'}, status=400)
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': settings.STRIPE_CURRENCY,
                'product_data': {
                    'name': f'Conference Paper Fee (Paper #{paper.id})',
                },
                'unit_amount': settings.STRIPE_PAYMENT_AMOUNT,
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=request.build_absolute_uri(f'/payment/success/{paper.id}/'),
        cancel_url=request.build_absolute_uri(f'/payment/cancel/{paper.id}/'),
        metadata={'paper_id': paper.id}
    )
    paper.stripe_session_id = session.id
    paper.save()
    return JsonResponse({'id': session.id, 'stripe_public_key': settings.STRIPE_PUBLISHABLE_KEY})

def payment_success(request, paper_id):
    paper = get_object_or_404(Paper, id=paper_id)
    paper.is_paid = True
    paper.save()
    return render(request, 'conference/payment_success.html', {'paper': paper})

def payment_cancel(request, paper_id):
    return render(request, 'conference/payment_cancel.html', {'paper_id': paper_id})

def send_paper_submission_emails(paper, conference, corresponding_author):
    """
    Send notification emails to chair and corresponding author when a paper is submitted.
    """
    try:
        # Email to the chair
        if conference.chair and conference.chair.email:
            chair_subject = f"New Paper Submission - {conference.name}"
            chair_message = f"""Dear {conference.chair.get_full_name() or conference.chair.username},

A new paper has been submitted to your conference \"{conference.name}\".

Paper Details:
- Title: {paper.title}
- Corresponding Author: {corresponding_author.first_name} {corresponding_author.last_name} ({corresponding_author.email})
- Submitted: {paper.submitted_at.strftime('%Y-%m-%d %H:%M:%S')}
- Abstract: {paper.abstract[:200]}{'...' if len(paper.abstract) > 200 else ''}

You can view and manage this submission through your conference dashboard.

Best regards,
PaperSetu Team"""

            send_mail(
                subject=chair_subject,
                message=chair_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[conference.chair.email],
                fail_silently=True,
            )

        # Email to the corresponding author
        if corresponding_author.email:
            author_subject = f"Paper Submission Confirmation - {conference.name}"
            author_message = f"""Dear {corresponding_author.first_name} {corresponding_author.last_name},

Your paper has been successfully submitted to the conference \"{conference.name}\".

Paper Details:
- Title: {paper.title}
- Conference: {conference.name}
- Submission Date: {paper.submitted_at.strftime('%Y-%m-%d %H:%M:%S')}
- Status: Submitted

Your paper is now under review. You will be notified of any updates regarding your submission.

Thank you for your submission!

Best regards,
{conference.name} Conference Team"""

            send_mail(
                subject=author_subject,
                message=author_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[corresponding_author.email],
                fail_silently=True,
            )

    except Exception as e:
        # Log the error but don't break the submission process
        print(f"Error sending paper submission emails: {e}")

def send_payment_request_email(author_email, paper):
    subject = "Your paper has been accepted! Please pay the conference fee"
    message = (
        f"Congratulations! Your paper '{paper.title}' has been accepted.\n\n"
        f"To proceed, please pay the conference fee of ₹{paper.payment_amount}.\n"
        f"Login to your dashboard and click the 'Pay Now' button.\n\n"
        f"Thank you!"
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [author_email],
        fail_silently=False,
    )

class SubreviewerReviewForm(forms.Form):
    RATING_CHOICES = [
        (5, 'Strong Accept (5)'),
        (4, 'Accept (4)'),
        (3, 'Weak Accept (3)'),
        (2, 'Weak Reject (2)'),
        (1, 'Reject (1)'),
        (0, 'Strong Reject (0)'),
    ]
    CONFIDENCE_CHOICES = [
        (5, 'Expert'),
        (4, 'High'),
        (3, 'Medium'),
        (2, 'Low'),
        (1, 'None'),
    ]
    rating = forms.ChoiceField(
        choices=RATING_CHOICES, 
        widget=forms.RadioSelect,
        required=True,
        help_text="Select your recommendation for this paper"
    )
    comments = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'Provide constructive feedback for the authors...'}),
        required=True,
        help_text="Comments that will be shared with the authors"
    )
    confidence = forms.ChoiceField(
        choices=CONFIDENCE_CHOICES, 
        widget=forms.RadioSelect,
        required=True,
        help_text="Your confidence level in this assessment"
    )
    remarks = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Confidential remarks for PC members only...'}),
        required=False, 
        label='Confidential Remarks for PC Members',
        help_text="These remarks are only visible to PC members and chairs"
    )

@login_required
def create_conference(request):
    if request.method == 'POST':
        form = ConferenceForm(request.POST)
        if form.is_valid():
            conference = form.save(commit=False)
            conference.chair = request.user
            conference.status = 'upcoming'
            conference.invite_link = get_random_string(32)
            conference.is_approved = False
            conference.requested_by = request.user
            conference.save()
            UserConferenceRole.objects.create(user=request.user, conference=conference, role='chair')
            # Send pending approval email to superuser(s) and organiser
            User = get_user_model()
            superusers = User.objects.filter(is_superuser=True)
            superuser_emails = [u.email for u in superusers if u.email]
            organiser_emails = []
            # Use the conference.contact_email as the organiser's email if provided
            if conference.contact_email:
                organiser_emails.append(conference.contact_email)
            # Also add the request user's email if available
            if hasattr(request.user, 'email') and request.user.email:
                organiser_emails.append(request.user.email)
            # Only include valid emails
            all_recipients = list(set([e for e in (superuser_emails + organiser_emails) if e and '@' in e]))
            if all_recipients:
                send_mail(
                    'Conference Request Pending',
                    f'A new conference request ("{conference.name}") is pending approval.',
                    'admin@example.com',
                    all_recipients,
                )
            return render(request, 'conference/conference_submitted.html', {'conference': conference})
        else:
            # Form is invalid, show errors and stay on the form
            return render(request, 'conference/create_conference.html', {'form': form})
    else:
        form = ConferenceForm()
    return render(request, 'conference/create_conference.html', {'form': form})

@login_required
def reviewer_volunteer(request):
    if hasattr(request.user, 'reviewer_profile'):
        messages.info(request, 'You have already volunteered as a reviewer.')
        return redirect('dashboard:dashboard')
    if request.method == 'POST':
        form = ReviewerVolunteerForm(request.POST)
        if form.is_valid():
            reviewer = form.save(commit=False)
            reviewer.user = request.user
            # Save first and last name to user
            request.user.first_name = form.cleaned_data['first_name']
            request.user.last_name = form.cleaned_data['last_name']
            request.user.save()
            reviewer.save()
            messages.success(request, 'Thank you for volunteering as a reviewer!')
            return redirect('dashboard:dashboard')
    else:
        form = ReviewerVolunteerForm()
    return render(request, 'conference/reviewer_volunteer.html', {'form': form})

@login_required
def submit_paper(request, conference_id):
    conference = get_object_or_404(Conference, id=conference_id)
    if request.method == 'POST':
        form = PaperSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            paper = form.save(commit=False)
            paper.author = request.user
            paper.conference = conference
            paper.submitted_at = timezone.now() # Add submitted_at field
            paper.save()
            UserConferenceRole.objects.get_or_create(user=request.user, conference=conference, role='author')
            # Get corresponding author
            corresponding_author = Author.objects.filter(paper=paper, is_corresponding=True).first()
            if corresponding_author:
                send_paper_submission_emails(paper, conference, corresponding_author)
            messages.success(request, 'Paper submitted successfully!')
            return redirect('dashboard:dashboard')
    else:
        form = PaperSubmissionForm()
    return render(request, 'conference/submit_paper.html', {'form': form, 'conference': conference})

@login_required
def join_conference(request, invite_link):
    from .models import UserConferenceRole
    try:
        conference = Conference.objects.get(invite_link=invite_link)
    except Conference.DoesNotExist:
        raise Http404('Conference not found.')
    user = request.user
    # Check if user has any roles in this conference
    user_roles = list(UserConferenceRole.objects.filter(user=user, conference=conference).values_list('role', flat=True))
    # If user is chair by FK, add it to roles if not present
    if conference.chair == user and 'chair' not in user_roles:
        user_roles.append('chair')
    is_author = 'author' in user_roles
    if user_roles:
        # User has roles, show choose_role page (with all their roles + Author)
        roles = set(user_roles)
        roles.add('author')  # Always show Author
        role_links = []
        for role in roles:
            if role == 'chair':
                url = reverse('dashboard:conference_submissions', args=[conference.id])
                label = 'Chair'
            elif role == 'author':
                url = reverse('conference:author_dashboard', args=[conference.id])
                label = 'Author (Upload Paper)'
            elif role == 'reviewer':
                url = reverse('dashboard:dashboard') + f'?view=reviewer&conf_id={conference.id}'
                label = 'Reviewer'
            elif role == 'pc_member':
                url = reverse('dashboard:pc_conference_detail', args=[conference.id])
                label = 'PC Member'
            elif role == 'subreviewer':
                url = reverse('dashboard:dashboard') + f'?view=subreviewer&conf_id={conference.id}'
                label = 'Subreviewer'
            else:
                continue
            role_links.append({'role': role, 'url': url, 'label': label})
        context = {'conference': conference, 'role_links': role_links}
        return render(request, 'conference/choose_role.html', context)
    # If user has no roles, allow join as author
    if request.method == 'POST':
        UserConferenceRole.objects.get_or_create(user=user, conference=conference, role='author')
        return redirect('conference:author_dashboard', conference_id=conference.id)
    return render(request, 'conference/join_conference.html', {'conference': conference, 'is_author': is_author})

@login_required
def conferences_list(request):
    """List all available conferences that the user can view"""
    search_query = request.GET.get('search', '')
    area_filter = request.GET.get('area', '')
    # Only show conferences where user is chair, pc_member, or author
    conferences = Conference.objects.filter(
        Q(chair=request.user) |
        Q(userconferencerole__user=request.user, userconferencerole__role__in=['author', 'pc_member'])
    ).distinct().filter(is_approved=True, status__in=['upcoming', 'live'])
    # Apply search filter
    if search_query:
        conferences = conferences.filter(
            Q(name__icontains=search_query) | 
            Q(acronym__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    # Apply area filter
    if area_filter:
        conferences = conferences.filter(primary_area=area_filter)
    # Add user role information
    for conference in conferences:
        conference.user_roles = UserConferenceRole.objects.filter(
            user=request.user, 
            conference=conference
        ).values_list('role', flat=True)
        if conference.chair == request.user and 'chair' not in conference.user_roles:
            conference.user_roles = list(conference.user_roles) + ['chair']
    from .models import AREA_CHOICES
    context = {
        'conferences': conferences,
        'search_query': search_query,
        'area_filter': area_filter,
        'area_choices': AREA_CHOICES,
    }
    return render(request, 'conference/conferences_list.html', context)

@login_required
def choose_conference_role(request, conference_id):
    from conference.models import SubreviewerInvite
    conference = get_object_or_404(Conference, id=conference_id)
    user = request.user
    roles = []
    if conference.chair == user:
        roles.append('chair')
    user_roles = UserConferenceRole.objects.filter(user=user, conference=conference).values_list('role', flat=True)
    for r in user_roles:
        if r not in roles:
            roles.append(r)
    # Always show pc_member if user has that role
    if 'pc_member' in user_roles and 'pc_member' not in roles:
        roles.append('pc_member')
    # Always show author role for everyone
    if 'author' not in roles:
        roles.append('author')
    # Show subreviewer role if user has UserConferenceRole or SubreviewerInvite (pending/accepted)
    has_subreviewer_role = 'subreviewer' in user_roles
    has_subreviewer_invite = SubreviewerInvite.objects.filter(paper__conference=conference, subreviewer=user, status__in=['invited', 'accepted']).exists()
    if (not has_subreviewer_role and has_subreviewer_invite) or has_subreviewer_role:
        if 'subreviewer' not in roles:
            roles.append('subreviewer')
    role_links = []
    for role in roles:
        if role == 'chair':
            url = reverse('dashboard:conference_submissions', args=[conference.id])
            label = 'Chair'
        elif role == 'author':
            url = reverse('conference:author_dashboard', args=[conference.id])
            label = 'Author (Upload Paper)'
        elif role == 'reviewer':
            url = reverse('dashboard:dashboard') + f'?view=reviewer&conf_id={conference.id}'
            label = 'Reviewer'
        elif role == 'pc_member':
            url = reverse('dashboard:pc_conference_detail', args=[conference.id])
            label = 'PC Member'
        elif role == 'subreviewer':
            url = reverse('conference:subreviewer_dashboard', args=[conference.id])
            label = 'Subreviewer'
        else:
            continue
        role_links.append({'role': role, 'url': url, 'label': label})
    context = {
        'conference': conference,
        'role_links': role_links,
    }
    return render(request, 'conference/choose_role.html', context)

@login_required
def author_dashboard(request, conference_id):
    from .forms import AuthorForm, PaperSubmissionForm
    from .models import Author
    conference = get_object_or_404(Conference, id=conference_id)
    user = request.user
    # Always fetch the latest status for each paper after any POST
    papers = Paper.objects.filter(conference=conference, author=user).order_by(
        models.Case(
            models.When(status='accepted', is_paid=False, then=0),
            default=1,
            output_field=models.IntegerField(),
        ),
        '-submitted_at'
    )
    message = ''
    if request.method == 'POST':
        paper_form = PaperSubmissionForm(request.POST, request.FILES)
        authors_data = request.POST.getlist('authors_json')
        import json
        authors = json.loads(authors_data[0]) if authors_data else []
        if paper_form.is_valid() and authors:
            paper = paper_form.save(commit=False)
            paper.author = user
            paper.conference = conference
            paper.submitted_at = timezone.now() # Add submitted_at field
            paper.save()
            # Save authors
            corresponding_found = False
            for idx, author in enumerate(authors):
                is_corr = bool(author.get('is_corresponding'))
                if is_corr:
                    if corresponding_found:
                        is_corr = False  # Only one corresponding author
                    else:
                        corresponding_found = True
                Author.objects.create(
                    paper=paper,
                    first_name=author.get('first_name', ''),
                    last_name=author.get('last_name', ''),
                    email=author.get('email', ''),
                    country_region=author.get('country_region', ''),
                    affiliation=author.get('affiliation', ''),
                    web_page=author.get('web_page', ''),
                    is_corresponding=is_corr
                )
            # Save keywords as a comma-separated string in Paper (add a keywords field if needed)
            paper.keywords = paper_form.cleaned_data['keywords']
            paper.save()
            UserConferenceRole.objects.get_or_create(user=user, conference=conference, role='author')
            # Get corresponding author
            corresponding_author = Author.objects.filter(paper=paper, is_corresponding=True).first()
            if corresponding_author:
                send_paper_submission_emails(paper, conference, corresponding_author)
            message = 'Paper submitted successfully!'
            papers = Paper.objects.filter(conference=conference, author=user)
        else:
            message = 'Please fill all required fields and add at least one author.'
    else:
        paper_form = PaperSubmissionForm()
    context = {
        'conference': conference,
        'papers': papers,
        'message': message,
        'paper_form': paper_form,
    }
    return render(request, 'conference/author_dashboard.html', context)

@login_required
def subreviewer_dashboard(request, conference_id):
    from conference.models import SubreviewerInvite, Review
    conference = get_object_or_404(Conference, id=conference_id)
    user = request.user
    invites = SubreviewerInvite.objects.filter(
        paper__conference=conference,
        subreviewer=user
    ).select_related('paper', 'invited_by')
    assigned_papers = []
    for invite in invites:
        review = Review.objects.filter(paper=invite.paper, reviewer=user).first()
        review_exists = review is not None
        status = invite.status
        can_answer = status == 'invited'
        can_review = status == 'accepted' and not review_exists
        review_status = None
        if status == 'accepted' and not review_exists:
            review_status = 'Incomplete'
        elif status == 'accepted' and review_exists:
            if review.decision:
                review_status = 'Approved'
            elif review.recommendation:
                review_status = 'Recommendation Submitted'
            else:
                review_status = 'Completed'
        assigned_papers.append({
            'paper': invite.paper,
            'invite': invite,
            'status': status,
            'can_answer': can_answer,
            'can_review': can_review,
            'review_status': review_status,
            'review': review,
        })
    nav_tabs = [
        {'label': 'Review Requests', 'active': True},
        {'label': 'Conference', 'active': False},
        {'label': 'News', 'active': False},
        {'label': 'Paper Setup', 'active': False},
    ]
    context = {
        'conference': conference,
        'assigned_papers': assigned_papers,
        'nav_tabs': nav_tabs,
    }
    return render(request, 'conference/subreviewer_dashboard.html', context)

@login_required
def subreviewer_answer_request(request, invite_id):
    from conference.models import SubreviewerInvite
    invite = get_object_or_404(SubreviewerInvite, id=invite_id, subreviewer=request.user)
    if invite.status != 'invited':
        return redirect('conference:subreviewer_dashboard', conference_id=invite.paper.conference.id)
    if request.method == 'POST':
        decision = request.POST.get('decision')
        if decision in ['accepted', 'declined']:
            invite.status = decision
            invite.responded_at = timezone.now()
            invite.save()
            # Send email to assigner
            assigner = invite.invited_by
            subject = f"Subreviewer Response for '{invite.paper.title}'"
            message = f"{request.user.get_full_name() or request.user.username} has {decision} the request to review the paper '{invite.paper.title}' for {invite.paper.conference.name}."
            send_mail(subject, message, None, [assigner.email])
            if decision == 'accepted':
                # Redirect to review form (to be implemented)
                return redirect('conference:subreviewer_review_form', invite_id=invite.id)
            else:
                return redirect('conference:subreviewer_dashboard', conference_id=invite.paper.conference.id)
    return render(request, 'conference/subreviewer_answer_request.html', {'invite': invite})

@login_required
def subreviewer_review_form(request, invite_id):
    from conference.models import SubreviewerInvite, Review
    invite = get_object_or_404(SubreviewerInvite, id=invite_id, subreviewer=request.user)
    if invite.status != 'accepted':
        return redirect('conference:subreviewer_dashboard', conference_id=invite.paper.conference.id)
    # Prevent duplicate reviews
    if Review.objects.filter(paper=invite.paper, reviewer=request.user).exists():
        return redirect('conference:subreviewer_dashboard', conference_id=invite.paper.conference.id)
    if request.method == 'POST':
        form = SubreviewerReviewForm(request.POST)
        if form.is_valid():
            # Determine recommendation based on rating (but don't set final decision)
            rating = int(form.cleaned_data['rating'])
            if rating >= 3:  # Strong Accept, Accept, Weak Accept
                recommendation = 'accept'
            else:  # Weak Reject, Reject, Strong Reject
                recommendation = 'reject'
            
            # Create review with recommendation but no final decision
            # The decision field will be null/empty until chair approves
            Review.objects.create(
                paper=invite.paper,
                reviewer=request.user,
                decision=None,  # No final decision - only recommendation
                recommendation=recommendation,  # Store the recommendation
                comments=form.cleaned_data['comments'],
                rating=rating,
                confidence=form.cleaned_data['confidence'],
                remarks=form.cleaned_data['remarks'],
            )
            
            # Send notification to chair about new subreviewer review
            from conference.models import Notification
            Notification.objects.create(
                recipient=invite.paper.conference.chair,
                notification_type='paper_review',
                title=f'New Subreviewer Review for "{invite.paper.title}"',
                message=f'Subreviewer {request.user.get_full_name() or request.user.username} has submitted a review with {recommendation} recommendation for paper "{invite.paper.title}".',
                related_paper=invite.paper,
                related_conference=invite.paper.conference
            )
            
            return redirect('conference:subreviewer_dashboard', conference_id=invite.paper.conference.id)
    else:
        form = SubreviewerReviewForm()
    return render(request, 'conference/subreviewer_review_form.html', {'form': form, 'invite': invite})

@login_required
def download_paper(request, paper_id):
    from conference.models import Paper
    paper = get_object_or_404(Paper, id=paper_id)
    # Only allow download if user is assigned as subreviewer or reviewer for this paper
    user = request.user
    is_subreviewer = paper.subreviewer_invites.filter(subreviewer=user, status__in=['invited', 'accepted']).exists()
    is_reviewer = paper.reviews.filter(reviewer=user).exists()
    if not (is_subreviewer or is_reviewer or paper.author == user or user == paper.conference.chair):
        raise Http404("You do not have permission to download this paper.")
    if not paper.file:
        raise Http404("Paper file not found.")
    file_path = paper.file.path
    if not os.path.exists(file_path):
        raise Http404("File does not exist.")
    response = FileResponse(open(file_path, 'rb'), as_attachment=True, filename=os.path.basename(file_path))
    return response

nav_items = [
    "Submissions", "Reviews", "Status", "PC", "Events",
    "Email", "Administration", "Conference", "News", "papersetu"
]
context = {
    # ... your existing context ...
    'nav_items': nav_items,
    # Optionally, set 'active_tab': 'Submissions' or whichever is active
} 

@csrf_exempt
def stripe_webhook(request):
    import os
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
    event = None
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except Exception:
        return HttpResponse(status=400)
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        paper_id = session['metadata']['paper_id']
        from .models import Paper
        paper = Paper.objects.get(id=paper_id)
        paper.is_paid = True
        paper.save()
    return HttpResponse(status=200) 

@login_required
def author_papers_view(request, conference_id):
    conference = get_object_or_404(Conference, id=conference_id)
    papers = Paper.objects.filter(conference=conference, author=request.user).order_by('-submitted_at')
    return render(request, 'conference/author_papers.html', {
        'conference': conference,
        'papers': papers,
    }) 

def search_conferences(request):
    """
    Search for conferences by theme, venue, city, country, title, or acronym.
    """
    from django.db.models import Q
    query = request.GET.get('q', '').strip()
    conferences = Conference.objects.filter(is_approved=True, status__in=['upcoming', 'live'])
    if query:
        conferences = conferences.filter(
            Q(name__icontains=query) |
            Q(acronym__icontains=query) |
            Q(theme_domain__icontains=query) |
            Q(venue__icontains=query) |
            Q(city__icontains=query) |
            Q(country__icontains=query)
        )
    context = {
        'search_query': query,
        'search_results': conferences,
    }
    return render(request, 'conference/search_results.html', context) 