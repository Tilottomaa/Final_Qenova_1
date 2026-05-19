from django.test import TestCase
from django.contrib.auth import get_user_model
from queue_system.models import Organization, QueueBooking, Token
from emergency_and_swap.models import EmergencyRequest, SlotSwap
import datetime

User = get_user_model()

class EmergencyAndSwapTestCase(TestCase):
    def setUp(self):
        self.customer1 = User.objects.create_user(username='customer1', password='password1', is_customer=True)
        self.customer2 = User.objects.create_user(username='customer2', password='password1', is_customer=True)
        self.customer3 = User.objects.create_user(username='customer3', password='password1', is_customer=True)
        
        self.org_user = User.objects.create_user(username='hospital', password='password1', is_organization=True)
        from accounts.models import OrganizationProfile
        self.org_profile = OrganizationProfile.objects.create(user=self.org_user, organization_name="Hospital")
        self.org = Organization.objects.create(account=self.org_profile)
        
        today = datetime.date.today()
        self.booking1 = QueueBooking.objects.create(user=self.customer1, organization=self.org, booking_date=today)
        self.token1 = Token.objects.create(user=self.customer1, organization=self.org, booking=self.booking1, booking_date=today, status='Waiting', serial_number='T-001')
        
        self.booking2 = QueueBooking.objects.create(user=self.customer2, organization=self.org, booking_date=today)
        self.token2 = Token.objects.create(user=self.customer2, organization=self.org, booking=self.booking2, booking_date=today, status='Waiting', serial_number='T-002')

        self.booking3 = QueueBooking.objects.create(user=self.customer3, organization=self.org, booking_date=today)
        self.token3 = Token.objects.create(user=self.customer3, organization=self.org, booking=self.booking3, booking_date=today, status='Waiting', serial_number='T-003')

    def test_submit_and_approve_emergency(self):
        req = EmergencyRequest.submitEmergency(token=self.token3, emergency_type='Medical')
        self.assertEqual(req.status, 'Pending')
        self.assertEqual(req.emergency_type, 'Medical')
        
        req.approveEmergency(reviewer=self.org_user, notes="Urgent medical assistance requested")
        self.assertEqual(req.status, 'Approved')
        
        # Verify Token priority status on customer3's token (which got shifted to the first slot, i.e. Token 1's row)
        c3_token = Token.objects.get(user=self.customer3)
        self.assertTrue(c3_token.is_priority)
        self.assertEqual(c3_token.id, self.token1.id)
        
        tokens_ordered = list(Token.objects.filter(organization=self.org, status='Waiting').order_by('id'))
        self.assertEqual(tokens_ordered[0].user, self.customer3)

    def test_slot_swap(self):
        swap = SlotSwap.requestSwap(self.token1, self.token2)
        self.assertEqual(swap.status, 'Pending')
        self.assertTrue(swap.validateSwap())

        approved = swap.approveSwap()
        self.assertTrue(approved)
        self.assertEqual(swap.status, 'Approved')
        
        t1_refreshed = Token.objects.get(id=self.token1.id)
        t2_refreshed = Token.objects.get(id=self.token2.id)
        
        self.assertEqual(t1_refreshed.user, self.customer2)
        self.assertEqual(t2_refreshed.user, self.customer1)
