from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from accounts.models import OrganizationProfile
from .models import Organization, QueueBooking, Token, Feedback
from .forms import QueueBookingForm, RescheduleBookingForm, FeedbackForm
import datetime


def org_list_view(request):
    query = request.GET.get('q', '')
    organizations = OrganizationProfile.objects.all()
    if query:
        organizations = organizations.filter(organization_name__icontains=query)
    return render(request, 'queue_system/org_list.html', {
        'organizations': organizations,
        'query': query
    })


def org_detail_view(request, org_id):
    org_profile = get_object_or_404(OrganizationProfile, id=org_id)
    organization, _ = Organization.objects.get_or_create(account=org_profile)
    capacity = organization.manageQueueCapacity()
    feedbacks = Feedback.viewFeedbackHistory(organization)
    avg_rating = Feedback.calculateRating(organization)

    user_feedback = None
    if request.user.is_authenticated and not request.user.is_organization:
        user_feedback = Feedback.objects.filter(user_id=request.user.id, organization_id=organization.id).first()

    return render(request, 'queue_system/org_detail.html', {
        'organization': organization,
        'org_user': org_profile,
        'capacity': capacity,
        'feedbacks': feedbacks,
        'avg_rating': avg_rating,
        'user_feedback': user_feedback,
    })


@login_required
def book_queue_view(request, org_id):
    if request.user.is_organization:
        messages.error(request, "Organizations cannot book queues.")
        return redirect('org_list')

    org_profile = get_object_or_404(OrganizationProfile, id=org_id)
    organization, _ = Organization.objects.get_or_create(account=org_profile)

    if request.method == 'POST':
        form = QueueBookingForm(request.POST)
        if form.is_valid():
            booking_date = form.cleaned_data.get('booking_date') or datetime.date.today()

            if not QueueBooking.checkAvailability(organization, booking_date):
                messages.error(request, "Sorry, daily limit reached.")
                return render(request, 'queue_system/booking_form.html', {'form': form, 'organization': organization})

            if QueueBooking.objects.filter(user=request.user, organization=organization,
                                           booking_date=booking_date).exists():
                messages.error(request, "You already have a booking.")
                return redirect('org_detail', org_id=org_id)

            booking = QueueBooking.objects.create(
                user=request.user,
                organization=organization,
                booking_date=booking_date
            )

            token_count = Token.objects.filter(organization=organization, booking_date=booking_date).count()
            serial = f"T-{token_count + 1:03d}"

            token = Token.objects.create(
                user=request.user,
                organization=organization,
                booking=booking,
                booking_date=booking_date,
                serial_number=serial
            )
            token.calculateEstimatedTime()

            messages.success(request, f"Booked! Token is {serial}.")
            return redirect('booking_success', token_id=token.id)
    else:
        form = QueueBookingForm()

    return render(request, 'queue_system/booking_form.html', {
        'form': form,
        'organization': organization,
        'org_user': org_profile
    })


@login_required
def booking_success_view(request, token_id):
    token = get_object_or_404(Token, id=token_id, user=request.user)
    estimated = token.calculateEstimatedTime()
    return render(request, 'queue_system/booking_success.html', {
        'token': token,
        'estimated_time': estimated.strftime('%I:%M %p') if estimated else 'N/A',
    })


@login_required
def queue_status_api(request, org_id):
    org_profile = get_object_or_404(OrganizationProfile, id=org_id)
    organization, _ = Organization.objects.get_or_create(account=org_profile)

    today = datetime.date.today()
    upcoming_tokens = Token.objects.filter(
        organization=organization,
        booking_date=today,
        status='Waiting'
    ).order_by('id')[:5]

    upcoming_list = [t.serial_number for t in upcoming_tokens]
    user_token = Token.objects.filter(
        organization=organization,
        user=request.user,
        booking_date=today,
        status='Waiting'
    ).first()

    user_position = None
    if user_token:
        user_position = Token.objects.filter(
            organization=organization,
            booking_date=today,
            status='Waiting',
            id__lt=user_token.id
        ).count() + 1

    data = {
        'current_token': organization.current_token.serial_number if organization.current_token else 'None',
        'queue_load': organization.queue_load,
        'waiting_time': organization.waiting_time,
        'upcoming_tokens': upcoming_list,
        'user_position': user_position,
        'user_token_serial': user_token.serial_number if user_token else None,
        'estimated_time': today.strftime('%I:%M %p'),
        'suggested_arrival': today.strftime('%I:%M %p'),
    }
    return JsonResponse(data)


@login_required
def cancel_booking_view(request, booking_id):
    booking = get_object_or_404(QueueBooking, id=booking_id, user=request.user)
    if request.method == 'POST':
        booking.cancelQueue()
        messages.success(request, 'Booking cancelled.')
        return redirect('dashboard')
    return render(request, 'queue_system/cancel_confirm.html', {'booking': booking})


@login_required
def reschedule_booking_view(request, booking_id):
    booking = get_object_or_404(QueueBooking, id=booking_id, user=request.user)
    if request.method == 'POST':
        form = RescheduleBookingForm(request.POST)
        if form.is_valid():
            new_date = form.cleaned_data['new_date']
            booking.rescheduleQueue(new_date)
            messages.success(request, f'Rescheduled to {new_date}.')
            return redirect('dashboard')
    else:
        form = RescheduleBookingForm()
    return render(request, 'queue_system/reschedule_form.html', {'form': form, 'booking': booking})


@login_required
def submit_feedback_view(request, org_id):
    if request.user.is_organization:
        messages.error(request, "Organizations cannot submit feedback.")
        return redirect('org_list')

    org_profile = get_object_or_404(OrganizationProfile, id=org_id)
    organization, _ = Organization.objects.get_or_create(account=org_profile)
    feedback_instance = Feedback.objects.filter(user_id=request.user.id, organization_id=organization.id).first()

    if request.method == 'POST':
        form = FeedbackForm(request.POST, instance=feedback_instance)
        if form.is_valid():
            rating = form.cleaned_data['rating']
            comment = form.cleaned_data['comment']
            Feedback.submitFeedback(
                user=request.user,
                organization=organization,
                rating=rating,
                comment=comment
            )
            messages.success(request, "Feedback submitted.")
            return redirect('org_detail', org_id=org_id)
    else:
        form = FeedbackForm(instance=feedback_instance)

    return render(request, 'queue_system/feedback_form.html', {
        'form': form,
        'org_user': org_profile,
        'organization': organization,
        'feedback': feedback_instance
    })
