from django import forms
from .models import Conference, ReviewerPool, Paper, EmailTemplate, RegistrationApplication, AREA_CHOICES, Author, Track

class ConferenceForm(forms.ModelForm):
    primary_area = forms.ChoiceField(choices=AREA_CHOICES, required=True)
    secondary_area = forms.ChoiceField(choices=AREA_CHOICES, required=False)
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=True,
        help_text='First day of the conference'
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=True,
        help_text='Last day of the conference'
    )
    web_page = forms.URLField(
        required=True,
        help_text='Conference website URL'
    )
    paper_submission_deadline = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=True,
        help_text='Deadline for paper submissions'
    )
    
    class Meta:
        model = Conference
        fields = [
            'name', 'acronym', 'web_page', 'venue', 'city', 'country',
            'estimated_submissions', 'start_date', 'end_date',
            'primary_area', 'secondary_area', 'area_notes',
            'organizer', 'organizer_web_page', 'contact_phone',
            'role', 'description', 'paper_submission_deadline', 'paper_format',
            'chair', 'chair_name', 'chair_email'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Enter conference title'}),
            'acronym': forms.TextInput(attrs={'placeholder': 'Short acronym (e.g., ICML, CVPR)'}),
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Describe your conference'}),
            'venue': forms.TextInput(attrs={'placeholder': 'Venue name'}),
            'city': forms.TextInput(attrs={'placeholder': 'City'}),
            'country': forms.TextInput(attrs={'placeholder': 'Country or Region'}),
            'paper_format': forms.TextInput(attrs={'placeholder': 'e.g., PDF, 8 pages, double-column'}),
            'chair': forms.HiddenInput(),
            'chair_name': forms.TextInput(attrs={'placeholder': 'Full name of the conference chair'}),
            'chair_email': forms.EmailInput(attrs={'placeholder': 'Chair email address'}),
            'organizer': forms.TextInput(attrs={'placeholder': 'Organizer name or organization'}),
            'organizer_web_page': forms.URLInput(attrs={'placeholder': 'https://organizer.com'}),
            'contact_phone': forms.TextInput(attrs={'placeholder': '+1234567890'}),
            'role': forms.TextInput(attrs={'placeholder': 'Your role (e.g., Chair, Organizer)'}),
            'area_notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Any additional notes about the conference area'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make required fields mandatory
        required_fields = [
            'name', 'acronym', 'description', 'venue', 'city', 'country',
            'start_date', 'end_date', 'paper_submission_deadline',
            'primary_area', 'paper_format', 'chair_name', 'chair_email'
        ]
        
        for field_name in required_fields:
            if field_name in self.fields:
                self.fields[field_name].required = True
                # Add asterisk to label
                if hasattr(self.fields[field_name], 'label'):
                    current_label = self.fields[field_name].label or field_name.replace('_', ' ').title()
                    self.fields[field_name].label = f"{current_label} *"
        
        # Exclude chair field from form validation since we set it in the view
        if 'chair' in self.fields:
            self.fields['chair'].required = False
            self.fields['chair'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        paper_submission_deadline = cleaned_data.get('paper_submission_deadline')
        
        # Validate dates
        if start_date and end_date:
            if start_date > end_date:
                raise forms.ValidationError("First day cannot be after the last day.")
        
        if paper_submission_deadline and start_date:
            if paper_submission_deadline > start_date:
                raise forms.ValidationError("Paper submission deadline cannot be after the conference start date.")
        
        # Validate acronym (should be unique)
        acronym = cleaned_data.get('acronym')
        if acronym:
            # Check if this is an update (instance exists) or new creation
            if hasattr(self, 'instance') and self.instance.pk:
                existing_conference = Conference.objects.filter(acronym__iexact=acronym).exclude(pk=self.instance.pk).first()
            else:
                existing_conference = Conference.objects.filter(acronym__iexact=acronym).first()
            
            if existing_conference:
                raise forms.ValidationError(f"A conference with the acronym '{acronym}' already exists.")
        
        return cleaned_data

    def clean_acronym(self):
        acronym = self.cleaned_data.get('acronym')
        if acronym:
            # Remove spaces and convert to uppercase
            acronym = acronym.strip().upper()
            # Check if it's alphanumeric
            if not acronym.replace('-', '').replace('_', '').isalnum():
                raise forms.ValidationError("Acronym should contain only letters, numbers, hyphens, and underscores.")
        return acronym

class ReviewerVolunteerForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    class Meta:
        model = ReviewerPool
        fields = ['first_name', 'last_name', 'expertise', 'bio']

class AuthorForm(forms.ModelForm):
    class Meta:
        model = Author
        fields = [
            'first_name', 'last_name', 'email', 'country_region', 'affiliation', 'web_page', 'is_corresponding'
        ]
        widgets = {
            'is_corresponding': forms.CheckboxInput(attrs={'class': 'corresponding-checkbox'}),
            'web_page': forms.URLInput(attrs={'placeholder': 'https://example.com'}),
        }

class PaperSubmissionForm(forms.ModelForm):
    keywords = forms.CharField(required=True, help_text='Comma-separated keywords')
    track = forms.ModelChoiceField(queryset=None, required=False, help_text='Select a track (if applicable)')

    class Meta:
        model = Paper
        fields = ['title', 'abstract', 'file', 'track']
        widgets = {
            'abstract': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        conference = kwargs.pop('conference', None)
        super().__init__(*args, **kwargs)
        if conference:
            self.fields['track'].queryset = conference.tracks.all()
            if not conference.tracks.exists():
                self.fields['track'].widget = forms.HiddenInput()
        else:
            self.fields['track'].queryset = Track.objects.none()

class ConferenceInfoForm(forms.ModelForm):
    """Form for basic conference information settings."""
    class Meta:
        model = Conference
        fields = [
            'name', 'acronym', 'contact_email', 'description', 'web_page',
            'venue', 'city', 'country', 'registration_fee', 'theme_domain'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'registration_fee': forms.NumberInput(attrs={'step': '0.01'}),
        }

class SubmissionSettingsForm(forms.ModelForm):
    """Form for submission-related settings."""
    submission_deadline = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        required=False
    )
    
    class Meta:
        model = Conference
        fields = [
            'blind_review', 'abstract_required', 'multiple_authors_allowed',
            'submission_deadline', 'max_paper_length', 'allow_supplementary',
            'paper_format'
        ]
        widgets = {
            'max_paper_length': forms.NumberInput(attrs={'min': 1, 'max': 50}),
        }

class ReviewingSettingsForm(forms.ModelForm):
    """Form for reviewing-related settings."""
    review_deadline = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        required=False
    )
    
    class Meta:
        model = Conference
        fields = [
            'reviewers_per_paper', 'review_deadline', 'paper_bidding_enabled',
            'review_form_enabled', 'confidence_scores_enabled'
        ]
        widgets = {
            'reviewers_per_paper': forms.NumberInput(attrs={'min': 1, 'max': 10}),
        }

class RebuttalSettingsForm(forms.ModelForm):
    """Form for rebuttal phase settings."""
    rebuttal_deadline = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        required=False
    )
    
    class Meta:
        model = Conference
        fields = [
            'allow_rebuttal_phase', 'rebuttal_deadline', 'rebuttal_word_limit'
        ]
        widgets = {
            'rebuttal_word_limit': forms.NumberInput(attrs={'min': 100, 'max': 2000}),
        }

class DecisionSettingsForm(forms.ModelForm):
    """Form for decision and final deadline settings."""
    decision_deadline = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        required=False
    )
    camera_ready_deadline = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        required=False
    )
    
    class Meta:
        model = Conference
        fields = ['decision_deadline', 'camera_ready_deadline']

class EmailTemplateForm(forms.ModelForm):
    """Form for editing email templates."""
    class Meta:
        model = EmailTemplate
        fields = ['subject', 'body', 'is_active']
        widgets = {
            'subject': forms.TextInput(attrs={'class': 'form-input w-full'}),
            'body': forms.Textarea(attrs={'rows': 8, 'class': 'form-textarea w-full'}),
        }

class RegistrationApplicationStepOneForm(forms.ModelForm):
    """First step of registration application - basic info"""
    registration_start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text="When should registration open for attendees?"
    )
    
    class Meta:
        model = RegistrationApplication
        fields = ['organizer', 'country_region', 'registration_start_date']
        widgets = {
            'organizer': forms.TextInput(attrs={
                'placeholder': 'Enter organizer name or organization',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'country_region': forms.TextInput(attrs={
                'placeholder': 'e.g., United States, Europe, Asia-Pacific',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
        }

class RegistrationApplicationStepTwoForm(forms.ModelForm):
    """Second step of registration application - attendance and details"""
    
    class Meta:
        model = RegistrationApplication
        fields = ['estimated_attendees', 'notes']
        widgets = {
            'estimated_attendees': forms.NumberInput(attrs={
                'min': 1,
                'max': 10000,
                'placeholder': 'Expected number of attendees',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Any additional notes or special requirements...',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
        }
