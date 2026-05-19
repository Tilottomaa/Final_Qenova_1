from django.db import models
from queue_system.models import Token

class EmergencyRequest(models.Model):
    token = models.OneToOneField(Token, on_delete=models.CASCADE, related_name='emergency_request', null=True, blank=True)
    emergency_type = models.CharField(max_length=100)
    document = models.FileField(upload_to='emergency_docs/', null=True, blank=True)
    status = models.CharField(max_length=50, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    @classmethod
    def submitEmergency(cls, token, emergency_type, document=None):
        return cls.objects.create(token=token, emergency_type=emergency_type, document=document)

    def uploadDocument(self, doc_file):
        self.document = doc_file
        self.save()

    def approveEmergency(self, reviewer=None, notes=None):
        self.status = 'Approved'
        self.notes = notes
        self.save()
        
        token = self.token
        today = token.booking_date
        waiting_tokens = list(Token.objects.filter(organization=token.organization, booking_date=today, status='Waiting').order_by('id'))
        if len(waiting_tokens) > 1:
            users = [t.user for t in waiting_tokens]
            bookings = [t.booking for t in waiting_tokens]
            
            for t in waiting_tokens:
                t.booking = None
                t.save()
                
            shifted_users = [users[-1]] + users[:-1]
            shifted_bookings = [bookings[-1]] + bookings[:-1]
            
            for idx, t in enumerate(waiting_tokens):
                t.user = shifted_users[idx]
                t.booking = shifted_bookings[idx]
                if idx == 0:
                    t.is_priority = True
                    t.priority_serial = f"P-{shifted_users[idx].username}"
                t.save()

    def rejectEmergency(self, reviewer=None, notes=None):
        self.status = 'Rejected'
        self.notes = notes
        self.save()

class SlotSwap(models.Model):
    requester_id = models.IntegerField()
    target_user_id = models.IntegerField()
    current_slot_id = models.IntegerField()
    requested_slot_id = models.IntegerField()
    status = models.CharField(max_length=50, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def requester(self):
        from django.contrib.auth import get_user_model
        return get_user_model().objects.get(id=self.requester_id)

    @property
    def target_user(self):
        from django.contrib.auth import get_user_model
        return get_user_model().objects.get(id=self.target_user_id)

    @property
    def current_slot(self):
        return Token.objects.get(id=self.current_slot_id)

    @current_slot.setter
    def current_slot(self, value):
        self.current_slot_id = value.id

    @property
    def requested_slot(self):
        return Token.objects.get(id=self.requested_slot_id)

    @requested_slot.setter
    def requested_slot(self, value):
        self.requested_slot_id = value.id

    @classmethod
    def requestSwap(cls, current_token, target_token):
        return cls.objects.create(
            requester_id=current_token.user.id,
            target_user_id=target_token.user.id,
            current_slot_id=current_token.id,
            requested_slot_id=target_token.id
        )

    def validateSwap(self):
        return self.status == 'Pending'

    def approveSwap(self):
        if not self.validateSwap():
            return False
            
        t1 = Token.objects.get(id=self.current_slot_id)
        t2 = Token.objects.get(id=self.requested_slot_id)
        u1, u2 = t1.user, t2.user
        b1, b2 = t1.booking, t2.booking
        
        # Clear bookings first to avoid UNIQUE constraint violations
        t1.booking = None
        t2.booking = None
        t1.save()
        t2.save()
        
        t1.user = u2
        t2.user = u1
        t1.booking = b2
        t2.booking = b1
        t1.save()
        t2.save()
        
        self.status = 'Approved'
        self.save()
        return True

    def rejectSwap(self):
        self.status = 'Rejected'
        self.save()

class EmergencyAnalytics:
    @classmethod
    def detectFakeEmergency(cls, request):
        return {'is_suspicious': False, 'reasons': [], 'recent_count': 0}
    @classmethod
    def generateEmergencyReport(cls, organization):
        return {}
    @classmethod
    def analyzeEmergencyTrends(cls, organization):
        return {}
