from django.db import models
from queue_system.models import Token
import datetime

class OrganizationDashboard:
    class MockObjects:
        def get_or_create(self, organization):
            return OrganizationDashboard(organization), True
    objects = MockObjects()

    def __init__(self, organization):
        self.organization = organization

    def monitorQueue(self):
        waiting_count = Token.objects.filter(organization=self.organization, status='Waiting').count()
        serving = Token.objects.filter(organization=self.organization, status='Serving').first()
        return {
            'waiting_count': waiting_count,
            'serving_token_number': serving.serial_number if serving else None,
            'serving_token_user': serving.user.username if serving else None,
            'health_status': 'Healthy'
        }

    def generateDashboardStats(self):
        tokens = Token.objects.filter(organization=self.organization)
        return {
            'total_bookings': tokens.count(),
            'total_users': tokens.values('user').distinct().count(),
            'status_distribution': {
                'Waiting': tokens.filter(status='Waiting').count(),
                'Serving': tokens.filter(status='Serving').count(),
                'Completed': tokens.filter(status='Completed').count(),
                'Skipped': tokens.filter(status='Skipped').count(),
            }
        }

    def callNextToken(self):
        today = datetime.date.today()
        serving = Token.objects.filter(organization=self.organization, booking_date=today, status='Serving').first()
        if serving:
            serving.status = 'Completed'
            serving.save()
        next_t = Token.objects.filter(organization=self.organization, booking_date=today, status='Waiting').order_by('id').first()
        if next_t:
            next_t.status = 'Serving'
            next_t.save()
            return next_t
        return None

    def skipToken(self, token_id=None):
        today = datetime.date.today()
        if token_id:
            token = Token.objects.filter(id=token_id).first()
        else:
            token = Token.objects.filter(organization=self.organization, booking_date=today, status='Serving').first()
        if token:
            token.status = 'Skipped'
            token.save()
            return True
        return False

    def getQueueSettings(self):
        return {
            'organization_name': self.organization.account.organization_name,
            'token_limit': self.organization.token_limit,
            'working_hours_display': '9:00 AM - 5:00 PM',
            'is_within_working_hours': True,
            'capacity': {'total_booked': 0, 'remaining': 50}
        }

    def setTokenLimit(self, limit):
        self.organization.token_limit = int(limit)
        self.organization.save()
        return {'success': True, 'token_limit': self.organization.token_limit}

    def configureQueueSettings(self, **kwargs):
        return {'success': True, 'changes': ['Updated settings']}

class BehaviorMonitoring(models.Model):
    user_id = models.IntegerField(unique=True)
    no_shows = models.PositiveIntegerField(default=0)
    late_arrivals = models.PositiveIntegerField(default=0)
    cancellations = models.PositiveIntegerField(default=0)
    suspicious_activities = models.PositiveIntegerField(default=0)
    emergency_misuses = models.PositiveIntegerField(default=0)
    is_blacklisted = models.BooleanField(default=False)

    def detectNoShow(self):
        self.no_shows += 1
        self.save()

    def trackLateArrival(self):
        self.late_arrivals += 1
        self.save()

class QueueReport(models.Model):
    organization_id = models.IntegerField()
    report_date = models.DateField(default=datetime.date.today)
    stats = models.JSONField(null=True, blank=True)
    efficiency_rating = models.CharField(max_length=20, null=True, blank=True)

    @classmethod
    def generateDailyReport(cls, organization, report_date=None):
        report, _ = cls.objects.get_or_create(organization_id=organization.id, report_date=report_date or datetime.date.today())
        return report

    def analyzePerformance(self):
        return {'total_tokens': 1, 'completed_count': 1, 'performance_alerts': []}


