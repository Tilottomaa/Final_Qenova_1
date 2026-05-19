from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import User
from .forms import UserRegistrationForm, OrganizationRegistrationForm, UserProfileForm, CustomAuthenticationForm
import datetime


def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Registered successfully!')
            return redirect('login')
    else:
        form = UserRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
                return redirect('dashboard')
    else:
        form = CustomAuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('home')


@login_required
def dashboard_view(request):
    if request.user.is_organization:
        return redirect('org_dashboard')

    from queue_system.models import Token
    from emergency_and_swap.models import SlotSwap
    user_tokens = Token.objects.filter(user=request.user).order_by('-id')
    incoming_swaps = SlotSwap.objects.filter(target_user_id=request.user.id, status='Pending')

    return render(request, 'accounts/dashboard.html', {
        'user_tokens': user_tokens,
        'incoming_swaps': incoming_swaps,
    })


def home_view(request):
    return render(request, 'accounts/home.html')


def org_register_view(request):
    if request.method == 'POST':
        form = OrganizationRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('org_login')
    else:
        form = OrganizationRegistrationForm()
    return render(request, 'accounts/org_register.html', {'form': form})


def org_login_view(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user and user.is_organization:
                login(request, user)
                return redirect('org_dashboard')
    else:
        form = CustomAuthenticationForm()
    return render(request, 'accounts/org_login.html', {'form': form})


@login_required
def org_dashboard_view(request):
    if not request.user.is_organization:
        return redirect('dashboard')

    from queue_system.models import Organization, Token
    org_profile = request.user.organization_profile
    organization, _ = Organization.objects.get_or_create(account=org_profile)

    today = datetime.date.today()
    waiting_tokens = Token.objects.filter(organization=organization, booking_date=today, status='Waiting').order_by(
        'id')

    return render(request, 'accounts/org_dashboard.html', {
        'organization': organization,
        'waiting_tokens': waiting_tokens,
        'flow_stats': organization.monitorQueueFlow(),
        'capacity': organization.manageQueueCapacity(),
    })


@login_required
def update_queue_status_view(request):
    return redirect('org_settings')


@login_required
def call_next_token_view(request):
    if request.method == 'POST' and request.user.is_organization:
        from queue_system.models import Organization
        from organization_panel.models import OrganizationDashboard
        org_profile = request.user.organization_profile
        organization, _ = Organization.objects.get_or_create(account=org_profile)
        dashboard = OrganizationDashboard(organization)
        next_token = dashboard.callNextToken()
        if next_token:
            messages.success(request, f'Serving token: {next_token.serial_number}')
    return redirect('org_dashboard')


@login_required
def skip_token_view(request, token_id=None):
    if request.method == 'POST' and request.user.is_organization:
        from queue_system.models import Organization
        from organization_panel.models import OrganizationDashboard
        org_profile = request.user.organization_profile
        organization, _ = Organization.objects.get_or_create(account=org_profile)
        dashboard = OrganizationDashboard(organization)
        dashboard.skipToken(token_id)
        messages.success(request, 'Token skipped.')
    return redirect('org_dashboard')


@login_required
def reset_queue_view(request):
    if request.method == 'POST' and request.user.is_organization:
        from queue_system.models import Organization
        org_profile = request.user.organization_profile
        organization, _ = Organization.objects.get_or_create(account=org_profile)
        organization.resetQueue()
        messages.success(request, 'Queue reset.')
    return redirect('org_dashboard')


@login_required
def set_token_limit_view(request):
    return redirect('org_settings')


@login_required
def set_working_hours_view(request):
    return redirect('org_settings')


@login_required
def profile_view(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'accounts/profile.html', {'form': form})


def activate_account_view(request, uidb64, token):
    return redirect('login')


@login_required
def org_live_status_api_view(request):
    if not request.user.is_organization:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    from queue_system.models import Organization, Token
    org_profile = request.user.organization_profile
    organization, _ = Organization.objects.get_or_create(account=org_profile)

    today = datetime.date.today()
    waiting_tokens = Token.objects.filter(organization=organization, booking_date=today, status='Waiting').order_by(
        'id')

    waiting_list = [{
        'id': t.id,
        'serial_number': t.serial_number,
        'username': t.user.username,
        'booked_at': t.booking.created_at.strftime('%Y-%m-%d') if t.booking else '—',
        'status': t.status
    } for t in waiting_tokens]

    return JsonResponse({
        'health_status': 'Healthy',
        'waiting_count': waiting_tokens.count(),
        'serving_token_number': organization.current_token.serial_number if organization.current_token else 'None',
        'serving_token_user': organization.current_token.user.username if organization.current_token else '',
        'queue_status': organization.queue_status,
        'waiting_list': waiting_list
    })

