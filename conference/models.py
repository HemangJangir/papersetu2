from django.conf import settings
from django.db import models
from accounts.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

AREA_CHOICES = [
    ('AI', 'Artificial Intelligence'),
    ('ML', 'Machine Learning'),
    ('DS', 'Data Science'),
    ('CV', 'Computer Vision'),
    ('NLP', 'Natural Language Processing'),
    ('SE', 'Software Engineering'),
    ('CN', 'Computer Networks'),
    ('SEC', 'Cyber Security'),
    ('HCI', 'Human-Computer Interaction'),
    ('DB', 'Databases'),
    ('IOT', 'Internet of Things'),
    ('BIO', 'Bioinformatics'),
    ('EDU', 'Education Technology'),
    ('GRAPH', 'Computer Graphics'),
    ('OTHER', 'Other'),
]

class Conference(models.Model):
    name = models.CharField(max_length=255)
    acronym = models.CharField(max_length=50, blank=True)
    web_page = models.URLField(blank=True)
    venue = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    estimated_submissions = models.IntegerField(null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    primary_area = models.CharField(max_length=50, choices=AREA_CHOICES, default='AI')
    secondary_area = models.CharField(max_length=50, choices=AREA_CHOICES, default='AI')
    area_notes = models.TextField(blank=True)
    organizer = models.CharField(max_length=255, blank=True)
    organizer_web_page = models.URLField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    role = models.CharField(max_length=100, blank=True)
    is_approved = models.BooleanField(default=False)
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requested_conferences', null=True, blank=True)
    description = models.TextField(blank=True)
    chair = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chaired_conferences')
    chair_name = models.CharField(max_length=255, blank=True, help_text="Conference chair's full name")
    chair_email = models.EmailField(blank=True, help_text="Conference chair's email address")
    status = models.CharField(max_length=20, choices=[('upcoming', 'Upcoming'), ('live', 'Live'), ('completed', 'Completed')], default='upcoming')
    invite_link = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paper_submission_deadline = models.DateField(null=True, blank=True)
    paper_format = models.CharField(max_length=10, choices=[('pdf', 'PDF'), ('docx', 'DOCX')], default='pdf')
    
    # Conference Info Settings
    contact_email = models.EmailField(blank=True, help_text="Main contact email for the conference")
    registration_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Registration fee amount")
    theme_domain = models.CharField(max_length=255, blank=True, help_text="Conference theme or domain")
    
    # Submission Settings
    blind_review = models.BooleanField(default=True)
    abstract_required = models.BooleanField(default=True)
    multiple_authors_allowed = models.BooleanField(default=True)
    submission_deadline = models.DateTimeField(null=True, blank=True, help_text="Final submission deadline")
    max_paper_length = models.IntegerField(default=10)
    allow_supplementary = models.BooleanField(default=False)
    
    # Reviewing Settings
    reviewers_per_paper = models.IntegerField(default=3)
    review_deadline = models.DateTimeField(null=True, blank=True, help_text="Review submission deadline")
    paper_bidding_enabled = models.BooleanField(default=False, help_text="Enable paper bidding for reviewers")
    review_form_enabled = models.BooleanField(default=True)
    confidence_scores_enabled = models.BooleanField(default=True)
    
    # Rebuttal Settings
    allow_rebuttal_phase = models.BooleanField(default=False, help_text="Enable author rebuttal phase")
    rebuttal_deadline = models.DateTimeField(null=True, blank=True, help_text="Rebuttal submission deadline")
    rebuttal_word_limit = models.IntegerField(default=500, help_text="Word limit for rebuttals")
    
    # Decision Settings
    decision_deadline = models.DateTimeField(null=True, blank=True, help_text="Final decision deadline")
    camera_ready_deadline = models.DateTimeField(null=True, blank=True, help_text="Camera-ready submission deadline")

    def __str__(self):
        return self.name

class ReviewerPool(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='reviewer_profile')
    expertise = models.CharField(max_length=255)
    bio = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.expertise}"

class ReviewInvite(models.Model):
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE, related_name='review_invites')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='review_invites')
    status = models.CharField(max_length=10, choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('declined', 'Declined')], default='pending')
    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invite: {self.reviewer} for {self.conference} ({self.status})"

class UserConferenceRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE)
    role = models.CharField(max_length=15, choices=[
        ('chair', 'Chair'),
        ('author', 'Author'),
        ('reviewer', 'Reviewer'),
        ('pc_member', 'PC Member'),
        ('subreviewer', 'Subreviewer'),
    ])
    track = models.ForeignKey('Track', on_delete=models.SET_NULL, null=True, blank=True, related_name='user_roles')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'conference', 'role')

    def __str__(self):
        return f"{self.user} - {self.role} @ {self.conference}"

class Track(models.Model):
    track_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    conference = models.ForeignKey('Conference', on_delete=models.CASCADE, related_name='tracks')
    chair = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='chaired_tracks')

    def __str__(self):
        return f"{self.name} ({self.track_id})"

class Paper(models.Model):
    title = models.CharField(max_length=255)
    abstract = models.TextField()
    file = models.FileField(upload_to='papers/')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='papers')
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE, related_name='papers')
    submitted_at = models.DateTimeField(auto_now_add=True)
    paper_id = models.CharField(max_length=20, unique=True, blank=True, null=True, help_text="Unique Paper ID for search/reference")
    track = models.ForeignKey(Track, on_delete=models.SET_NULL, null=True, blank=True, related_name='papers')
    
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_paid = models.BooleanField(default=False)
    stripe_session_id = models.CharField(max_length=255, blank=True, null=True)
    payment_amount = models.PositiveIntegerField(default=500)  # in INR
    is_final_list = models.BooleanField(default=False, help_text="Mark if this paper is included in the final endorsed list")
    keywords = models.CharField(max_length=255, blank=True, help_text="Comma-separated keywords")
    plagiarism_percentage = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Plagiarism percentage (0-100)")

    def __str__(self):
        return self.title
    
    def update_status_based_on_reviews(self):
        """Update paper status based on review decisions"""
        # Only update internal review state, do not set status to accepted/rejected automatically
        # Status remains 'pending' until chair acts
        pass

    def save(self, *args, **kwargs):
        if not self.paper_id:
            acronym = (self.conference.acronym or 'CONF').upper()
            year = self.conference.start_date.year if self.conference.start_date else 0
            yy = str(year)[-2:] if year else 'XX'
            serial = Paper.objects.filter(
                conference=self.conference,
                submitted_at__year=year
            ).count() + 1
            self.paper_id = f"{acronym}{yy}{serial:02d}"
        super().save(*args, **kwargs)

class Review(models.Model):
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    decision = models.CharField(max_length=10, choices=[('accept', 'Accept'), ('reject', 'Reject')], blank=True, null=True)
    recommendation = models.CharField(max_length=10, choices=[('accept', 'Accept'), ('reject', 'Reject')], blank=True, null=True, help_text="Subreviewer recommendation (not final decision)")
    submitted_at = models.DateTimeField(auto_now_add=True)
    comments = models.TextField(blank=True)
    rating = models.IntegerField(null=True, blank=True)
    confidence = models.IntegerField(null=True, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        unique_together = ('paper', 'reviewer')

    def __str__(self):
        if self.decision:
            return f"{self.reviewer} review for {self.paper}: {self.decision}"
        elif self.recommendation:
            return f"{self.reviewer} review for {self.paper}: {self.recommendation} (recommendation)"
        else:
            return f"{self.reviewer} review for {self.paper}: pending"

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('reviewer_invite', 'Reviewer Invitation'),
        ('reviewer_response', 'Reviewer Response'),
        ('paper_assignment', 'Paper Assignment'),
        ('paper_review', 'Paper Review'),
        ('paper_decision', 'Paper Decision'),
    ]
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    related_conference = models.ForeignKey(Conference, on_delete=models.CASCADE, null=True, blank=True)
    related_paper = models.ForeignKey(Paper, on_delete=models.CASCADE, null=True, blank=True)
    related_review_invite = models.ForeignKey(ReviewInvite, on_delete=models.CASCADE, null=True, blank=True)
    related_review = models.ForeignKey(Review, on_delete=models.CASCADE, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient.username} - {self.title}"

class PCInvite(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('cancelled', 'Cancelled'),
        ('declined', 'Declined'),
    ]
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE, related_name='pc_invites')
    email = models.EmailField()
    name = models.CharField(max_length=255, blank=True)
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pc_invites_sent')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    sent_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    token = models.CharField(max_length=64, unique=True)
    track = models.ForeignKey(Track, on_delete=models.SET_NULL, null=True, blank=True, related_name='pc_invites')

    def __str__(self):
        return f"{self.email} invited to {self.conference} ({self.status})"

class ConferenceAdminSettings(models.Model):
    """
    Stores administration panel toggle states for each chair per conference.
    """
    conference = models.OneToOneField(Conference, on_delete=models.CASCADE, related_name='admin_settings')
    chair = models.ForeignKey(User, on_delete=models.CASCADE, related_name='admin_settings')
    
    # Toggle switches for admin features
    configure_enabled = models.BooleanField(default=True)
    workflow_enabled = models.BooleanField(default=False)
    registration_enabled = models.BooleanField(default=False)
    other_utilities_enabled = models.BooleanField(default=False)
    analytics_enabled = models.BooleanField(default=False)
    statistics_enabled = models.BooleanField(default=True)
    demo_version_enabled = models.BooleanField(default=False)
    tracks_enabled = models.BooleanField(default=False)
    create_cfp_enabled = models.BooleanField(default=False)
    create_program_enabled = models.BooleanField(default=False)
    create_proceedings_enabled = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('conference', 'chair')
        verbose_name = 'Conference Admin Settings'
        verbose_name_plural = 'Conference Admin Settings'
    
    def __str__(self):
        return f"Admin Settings for {self.conference.name} by {self.chair.username}"
    
    @classmethod
    def get_or_create_for_conference(cls, conference, chair):
        """Get or create admin settings with default values for a conference and chair."""
        settings, created = cls.objects.get_or_create(
            conference=conference,
            chair=chair,
            defaults={
                'configure_enabled': True,
                'workflow_enabled': False,
                'registration_enabled': False,
                'other_utilities_enabled': False,
                'analytics_enabled': False,
                'statistics_enabled': True,
                'demo_version_enabled': False,
                'tracks_enabled': False,
                'create_cfp_enabled': False,
                'create_program_enabled': False,
                'create_proceedings_enabled': False,
            }
        )
        return settings
    
    def get_enabled_features_count(self):
        """Return the count of enabled features."""
        enabled_features = [
            self.configure_enabled,
            self.workflow_enabled,
            self.registration_enabled,
            self.other_utilities_enabled,
            self.analytics_enabled,
            self.statistics_enabled,
            self.demo_version_enabled,
            self.tracks_enabled,
            self.create_cfp_enabled,
            self.create_program_enabled,
            self.create_proceedings_enabled,
        ]
        return sum(enabled_features)

class RegistrationApplication(models.Model):
    """
    Model for registration application requests from chairs.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    conference = models.OneToOneField(Conference, on_delete=models.CASCADE, related_name='registration_application')
    organizer = models.CharField(max_length=255, help_text="Individual or organization name")
    country_region = models.CharField(max_length=100, help_text="Country or region")
    registration_start_date = models.DateField(help_text="When registration opens")
    estimated_attendees = models.IntegerField(help_text="Expected number of attendees")
    
    # Application status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    applied_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_applications')
    
    # Additional fields
    notes = models.TextField(blank=True, help_text="Additional notes or requirements")
    admin_notes = models.TextField(blank=True, help_text="Admin notes for review")
    
    class Meta:
        verbose_name = 'Registration Application'
        verbose_name_plural = 'Registration Applications'
    
    def __str__(self):
        return f"Registration Application for {self.conference.name} - {self.status}"

class EmailTemplate(models.Model):
    """
    Email templates for various conference communications.
    """
    TEMPLATE_TYPES = [
        ('submission_confirmation', 'Submission Confirmation'),
        ('review_invitation', 'Review Invitation'),
        ('review_reminder', 'Review Reminder'),
        ('decision_accept', 'Decision - Accept'),
        ('decision_reject', 'Decision - Reject'),
        ('rebuttal_invitation', 'Rebuttal Invitation'),
        ('camera_ready_request', 'Camera Ready Request'),
        ('registration_confirmation', 'Registration Confirmation'),
    ]
    
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE, related_name='email_templates')
    template_type = models.CharField(max_length=50, choices=TEMPLATE_TYPES)
    subject = models.CharField(max_length=255, help_text="Email subject line")
    body = models.TextField(help_text="Email body content (HTML allowed)")
    is_active = models.BooleanField(default=True, help_text="Whether this template is active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('conference', 'template_type')
        verbose_name = 'Email Template'
        verbose_name_plural = 'Email Templates'
    
    def __str__(self):
        return f"{self.conference.name} - {self.get_template_type_display()}"
    
    @classmethod
    def get_default_templates(cls):
        """Return default email templates."""
        return {
            'submission_confirmation': {
                'subject': 'Submission Confirmation - {conference_name}',
                'body': '''Dear {author_name},\n\nThank you for your submission to {conference_name}.\n\nPaper Title: {paper_title}\nSubmission ID: {submission_id}\nSubmission Date: {submission_date}\n\nYour submission is now under review. You will be notified once the review process is complete.\n\nBest regards,\n{conference_name} Organizing Committee'''
            },
            'review_invitation': {
                'subject': 'Review Invitation - {conference_name}',
                'body': '''Dear {reviewer_name},\n\nYou are invited to review a paper for {conference_name}.\n\nPaper Title: {paper_title}\nReview Deadline: {review_deadline}\n\nPlease log in to your reviewer dashboard to accept or decline this invitation.\n\nBest regards,\n{conference_name} Program Committee'''
            },
            'decision_accept': {
                'subject': 'Paper Acceptance - {conference_name}',
                'body': '''Dear {author_name},\n\nCongratulations! Your paper has been accepted for {conference_name}.\n\nPaper Title: {paper_title}\n\nPlease prepare your camera-ready version by {camera_ready_deadline}.\n\nBest regards,\n{conference_name} Program Committee'''
            },
            'decision_reject': {
                'subject': 'Paper Decision - {conference_name}',
                'body': '''Dear {author_name},\n\nThank you for your submission to {conference_name}.\n\nPaper Title: {paper_title}\n\nAfter careful review, we regret to inform you that your paper was not selected for acceptance.\n\nWe encourage you to submit to future conferences.\n\nBest regards,\n{conference_name} Program Committee'''
            }
        }

class SubreviewerInvite(models.Model):
    STATUS_CHOICES = [
        ('invited', 'Invited'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('cancelled', 'Cancelled'),
    ]
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name='subreviewer_invites')
    subreviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subreviewer_invites')
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subreviewer_invited_by')
    email = models.EmailField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='invited')
    requested_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    token = models.CharField(max_length=64, unique=True)
    track = models.ForeignKey(Track, on_delete=models.SET_NULL, null=True, blank=True, related_name='subreviewer_invites')

    def __str__(self):
        return f"{self.subreviewer} invited for {self.paper} ({self.status})"

class Author(models.Model):
    paper = models.ForeignKey('Paper', on_delete=models.CASCADE, related_name='authors')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    country_region = models.CharField(max_length=100)
    affiliation = models.CharField(max_length=255)
    web_page = models.URLField(blank=True)
    is_corresponding = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({'Corresponding' if self.is_corresponding else 'Author'})"

FEATURE_CHOICES = [
    ('config', 'Config'),
    ('registration', 'Registration'),
    ('utilities', 'Other Utilities'),
    ('analytics', 'Analytics'),
    ('statistics', 'Statistics'),
    ('demo', 'Demo Version'),
    ('tracks', 'Tracks'),
    ('cfp', 'Create CFP'),
    ('program', 'Create Program'),
    ('proceedings', 'Create Proceedings'),
]

class ConferenceFeatureToggle(models.Model):
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE, related_name='feature_toggles')
    feature = models.CharField(max_length=32, choices=FEATURE_CHOICES)
    enabled = models.BooleanField(default=True)

    class Meta:
        unique_together = ('conference', 'feature')
        verbose_name = 'Conference Feature Toggle'
        verbose_name_plural = 'Conference Feature Toggles'

    def __str__(self):
        return f"{self.conference.name} - {self.get_feature_display()} ({'Enabled' if self.enabled else 'Disabled'})"

@receiver(post_save, sender=Conference)
def create_feature_toggles_for_conference(sender, instance, created, **kwargs):
    if created:
        for feature, _ in FEATURE_CHOICES:
            ConferenceFeatureToggle.objects.get_or_create(conference=instance, feature=feature, defaults={'enabled': True})
