from django.contrib import admin
from .models import EmergencyRequest, SlotSwap

@admin.register(EmergencyRequest)
class EmergencyRequestAdmin(admin.ModelAdmin):
    list_display = ('token', 'emergency_type', 'status', 'created_at')
    list_filter = ('status', 'emergency_type')
    search_fields = ('token__serial_number', 'token__user__username')

@admin.register(SlotSwap)
class SlotSwapAdmin(admin.ModelAdmin):
    list_display = ('id', 'requester_id', 'target_user_id', 'current_slot_id', 'requested_slot_id', 'status', 'created_at')
    list_filter = ('status',)
