from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from queue_system.models import Token, Organization
from .models import EmergencyRequest, SlotSwap, EmergencyAnalytics

@login_required
def submit_emergency_view(request, token_id):
    token = get_object_or_404(Token, id=token_id, user=request.user)

    if request.method == 'POST':
        from .forms import EmergencyRequestForm
        form = EmergencyRequestForm(request.POST, request.FILES)
        if form.is_valid():
            req = form.save(commit=False)
            req.token = token
            req.save()
            messages.success(request, "Emergency request submitted.")
            return redirect('dashboard')
    else:
        from .forms import EmergencyRequestForm
        form = EmergencyRequestForm()

    return render(request, 'emergency_and_swap/submit_emergency.html', {
        'form': form,
        'token': token,
        'organization': token.organization
    })

@login_required
def org_emergencies_view(request):
    if not request.user.is_organization:
        return redirect('dashboard')

    org_profile = request.user.organization_profile
    organization = get_object_or_404(Organization, account=org_profile)
    requests = EmergencyRequest.objects.filter(token__organization=organization).order_by('-created_at')

    request_data = [{
        'req': r,
        'is_suspicious': False,
        'reasons': [],
        'recent_count': 0
    } for r in requests]

    return render(request, 'emergency_and_swap/org_emergencies.html', {
        'requests': request_data,
        'organization': organization,
        'active_prios': Token.objects.filter(organization=organization, status='Waiting', is_priority=True),
        'total_waiting_count': Token.objects.filter(organization=organization, status='Waiting').count(),
        'trends': {}
    })

@login_required
def approve_emergency_view(request, request_id):
    if not request.user.is_organization:
        return redirect('dashboard')

    req = get_object_or_404(EmergencyRequest, id=request_id)
    req.approveEmergency(reviewer=request.user)
    messages.success(request, "Approved.")
    return redirect('org_emergencies')

@login_required
def reject_emergency_view(request, request_id):
    if not request.user.is_organization:
        return redirect('dashboard')

    req = get_object_or_404(EmergencyRequest, id=request_id)
    req.rejectEmergency(reviewer=request.user)
    messages.warning(request, "Rejected.")
    return redirect('org_emergencies')

@login_required
def swap_list_view(request, token_id):
    token = get_object_or_404(Token, id=token_id, user=request.user)
    other_tokens = Token.objects.filter(organization=token.organization, booking_date=token.booking_date, status='Waiting').exclude(id=token.id)
    sent_requests = SlotSwap.objects.filter(current_slot_id=token.id)
    sent_target_ids = [s.requested_slot_id for s in sent_requests]

    return render(request, 'emergency_and_swap/swap_list.html', {
        'token': token,
        'other_tokens': other_tokens,
        'sent_target_ids': sent_target_ids,
        'organization': token.organization
    })

@login_required
def request_swap_view(request, token_id, target_token_id):
    token = get_object_or_404(Token, id=token_id, user=request.user)
    target_token = get_object_or_404(Token, id=target_token_id)

    SlotSwap.requestSwap(token, target_token)
    messages.success(request, "Swap request sent.")
    return redirect('swap_list', token_id=token_id)

@login_required
def approve_swap_view(request, swap_id):
    swap = get_object_or_404(SlotSwap, id=swap_id, target_user_id=request.user.id)
    if swap.status == 'Pending':
        swap.approveSwap()
        messages.success(request, "Approved.")
    return redirect('dashboard')

@login_required
def reject_swap_view(request, swap_id):
    swap = get_object_or_404(SlotSwap, id=swap_id, target_user_id=request.user.id)
    if swap.status == 'Pending':
        swap.rejectSwap()
        messages.warning(request, "Rejected.")
    return redirect('dashboard')

@login_required
def adjust_priority_position_view(request, priority_id):
    return redirect('org_emergencies')
