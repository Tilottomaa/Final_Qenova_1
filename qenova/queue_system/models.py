from django.db import models
from django.conf import settings
from accounts.models import OrganizationProfile
import datetime

class Organization(models.Model):
    account = models.OneToOneField(OrganizationProfile, on_delete=models.CASCADE, related_name='queue_profile')
    type = models.CharField(max_length=100, default='General')
    token_limit = models.IntegerField(default=50)
    queue_status = models.CharField(max_length=50, default='Active')
    work_start = models.TimeField(null=True, blank=True)
    work_end = models.TimeField(null=True, blank=True)

    current_token_id = models.IntegerField(null=True, blank=True)
    queue_load = models.IntegerField(default=0)
    waiting_time = models.IntegerField(default=0)

    def __str__(self):
        return self.account.organization_name

    def isWithinWorkingHours(self):
        return True

    def getWorkingHoursDisplay(self):
        return "9:00 AM - 5:00 PM"

    def setTokenLimit(self, limit):
        self.token_limit = limit
        self.save()

    def resetQueue(self):
        Token.objects.filter(organization=self, status='Waiting').update(status='Skipped')
        self.current_token_id = None
        self.queue_load = 0
        self.waiting_time = 0
        self.save()

    def manageQueueCapacity(self):
        total = Token.objects.filter(organization=self, booking_date=datetime.date.today()).count()
        return {
            'total_booked': total,
            'remaining': max(0, self.token_limit - total),
            'is_full': total >= self.token_limit,
            'token_limit': self.token_limit
        }

    @property
    def tracker(self):
        return self

    @property
    def current_token(self):
        return Token.objects.filter(organization=self, status='Serving').first()

    def refreshQueue(self):
        waiting = Token.objects.filter(organization=self, status='Waiting').count()
        self.queue_load = waiting
        self.waiting_time = waiting * 5
        self.save()

    def monitorQueueFlow(self):
        return {
            'waiting': Token.objects.filter(organization=self, status='Waiting').count(),
            'serving': Token.objects.filter(organization=self, status='Serving').count(),
            'completed': Token.objects.filter(organization=self, status='Completed').count(),
            'skipped': Token.objects.filter(organization=self, status='Skipped').count(),
            'health': 'Normal',
            'queue_status': self.queue_status
        }

class QueueBooking(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    booking_date = models.DateField()
    queue_position = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def cancelQueue(self):
        Token.objects.filter(booking=self).update(status='Skipped')
        self.delete()

    def rescheduleQueue(self, new_date):
        self.booking_date = new_date
        self.save()
        Token.objects.filter(booking=self).update(booking_date=new_date)

    @classmethod
    def checkAvailability(cls, organization, booking_date):
        total = cls.objects.filter(organization=organization, booking_date=booking_date).count()
        return total < organization.token_limit


class Token(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    booking = models.OneToOneField(QueueBooking, on_delete=models.CASCADE, null=True, blank=True)
    serial_number = models.CharField(max_length=20)
    booking_date = models.DateField()
    status = models.CharField(max_length=50, default='Waiting')
    estimated_time = models.DateTimeField(null=True, blank=True)
    served_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_priority = models.BooleanField(default=False)
    priority_serial = models.CharField(max_length=20, blank=True, null=True)
    priority_position = models.IntegerField(null=True, blank=True)

    def updateStatus(self, new_status):
        self.status = new_status
        self.save()

    def calculateEstimatedTime(self):
        self.estimated_time = datetime.datetime.now()
        self.save()
        return self.estimated_time

    @property
    def priority_info(self):
        if self.is_priority:
            class PriorityProxy:
                def __init__(self, t):
                    self.priority_serial = t.priority_serial
                    self.insertion_position = t.priority_position
                    self.urgency_level = 'High'
            return PriorityProxy(self)
        return None

class Feedback(models.Model):
    user_id = models.IntegerField()
    organization_id = models.IntegerField()
    rating = models.IntegerField()
    comment = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def submitFeedback(cls, user, organization, rating, comment=''):
        return cls.objects.create(user_id=user.id, organization_id=organization.id, rating=rating, comment=comment), True

    @classmethod
    def viewFeedbackHistory(cls, organization):
        return cls.objects.filter(organization_id=organization.id)

    @classmethod
    def calculateRating(cls, organization):
        return 4.5
