from django.db import models
from conference.models import Conference, EmailTemplate
from conference.models import User

class PCEmailLog(models.Model):
    conference = models.ForeignKey(Conference, on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sent_pc_emails')
    subject = models.CharField(max_length=200)
    body = models.TextField()
    recipients = models.TextField()  # Comma-separated emails
    sent_at = models.DateTimeField(auto_now_add=True)
    attachment_name = models.CharField(max_length=255, blank=True, null=True)
    template_used = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.subject} to {self.recipients} at {self.sent_at}" 