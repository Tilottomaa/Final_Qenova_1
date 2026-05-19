from django.test import TestCase
from django.contrib.auth import get_user_model
from queue_system.models import Token, Organization
from accounts.models import OrganizationProfile
from organization_panel.models import OrganizationDashboard, BehaviorMonitoring, QueueReport
import datetime

User = get_user_model()

class OrganizationDashboardTestCase(TestCase):
    def setUp(self):
        self.org_user = User.objects.create_user(
            username='TestHospital',
            email='test@hospital.com',
            password='password123',
            is_organization=True
        )
        self.org_profile = OrganizationProfile.objects.create(
            user=self.org_user,
            organization_name='Test Hospital'
        )
        self.org = Organization.objects.create(
            account=self.org_profile,
            token_limit=10,
            work_start=datetime.time(9, 0),
            work_end=datetime.time(17, 0),
        )
        
        self.customer1 = User.objects.create_user(
            username='customer1',
            email='c1@test.com',
            password='password123',
            is_customer=True
        )
        self.customer2 = User.objects.create_user(
            username='customer2',
            email='c2@test.com',
            password='password123',
            is_customer=True
        )

        today = datetime.date.today()
        self.t1 = Token.objects.create(
            user=self.customer1,
            organization=self.org,
            booking_date=today,
            serial_number='T-001',
            status='Waiting'
        )
        self.t2 = Token.objects.create(
            user=self.customer2,
            organization=self.org,
            booking_date=today,
            serial_number='T-002',
            status='Serving'
        )

    def test_dashboard_monitoring_and_stats(self):
        dashboard = OrganizationDashboard(self.org)
        
        mon = dashboard.monitorQueue()
        self.assertEqual(mon['waiting_count'], 1)
        self.assertEqual(mon['serving_token_number'], 'T-002')
        self.assertEqual(mon['serving_token_user'], 'customer2')
        self.assertEqual(mon['health_status'], 'Healthy')

        stats = dashboard.generateDashboardStats()
        self.assertEqual(stats['total_bookings'], 2)
        self.assertEqual(stats['total_users'], 2)
        self.assertEqual(stats['status_distribution']['Waiting'], 1)
        self.assertEqual(stats['status_distribution']['Serving'], 1)

    def test_call_and_skip_token(self):
        dashboard = OrganizationDashboard(self.org)
        
        next_token = dashboard.callNextToken()
        self.assertIsNotNone(next_token)
        self.assertEqual(next_token.serial_number, 'T-001')
        self.assertEqual(next_token.status, 'Serving')
        
        self.t2.refresh_from_db()
        self.assertEqual(self.t2.status, 'Completed')

        skipped = dashboard.skipToken()
        self.assertTrue(skipped)
        
        self.t1.refresh_from_db()
        self.assertEqual(self.t1.status, 'Skipped')

    def test_behavior_monitoring(self):
        profile, _ = BehaviorMonitoring.objects.get_or_create(user_id=self.customer1.id)
        
        profile.detectNoShow()
        self.assertEqual(profile.no_shows, 1)
        
        profile.trackLateArrival()
        self.assertEqual(profile.late_arrivals, 1)


