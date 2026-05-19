from django.contrib import admin
from .models import Organization, QueueBooking, Token, Feedback

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('id', 'account', 'type', 'token_limit', 'queue_status')

@admin.register(QueueBooking)
class QueueBookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'organization', 'booking_date', 'queue_position')

@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ('serial_number', 'user', 'organization', 'status', 'booking_date')

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'organization_id', 'rating', 'submitted_at')
    list_filter = ('rating', 'submitted_at')
