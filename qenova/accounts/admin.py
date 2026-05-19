from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, OrganizationProfile

class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Custom Info', {'fields': ('is_customer', 'is_organization', 'profile_picture')}),
    )
    list_display = ('username', 'email', 'is_active', 'is_customer', 'is_organization', 'is_staff')
    list_filter = ('is_active', 'is_customer', 'is_organization', 'is_staff')

admin.site.register(User, UserAdmin)
admin.site.register(OrganizationProfile)
