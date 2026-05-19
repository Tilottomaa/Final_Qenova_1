from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from queue_system.models import Organization
from .models import (
    BehaviorMonitoring,
    OrganizationDashboard,
    QueueReport,
)

def _get_organization_for_user(user):
    org_profile = user.organization_profile
    organization, _ = Organization.objects.get_or_create(account=org_profile)
    return organization







@login_required
def organization_settings_view(request):
    organization = _get_organization_for_user(request.user)
    dashboard = OrganizationDashboard(organization)

    if request.method == 'POST':
        limit = request.POST.get('token_limit')
        if limit:
            dashboard.setTokenLimit(limit)
            messages.success(request, 'Token limit updated.')
        return redirect('org_settings')

    settings = dashboard.getQueueSettings()
    return render(request, 'organization_panel/organization_settings.html', {
        'organization': organization,
        'dashboard': dashboard,
        'settings': settings,
    })

