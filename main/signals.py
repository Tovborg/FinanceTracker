from allauth.account.signals import user_logged_in, user_signed_up
from django.dispatch import receiver
from main.models import UserProfile
from .utils.utils import get_client_ip, get_geoip_data
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string


@receiver(user_logged_in)
def check_user_profile(sender, request, user, **kwargs):
    """
    Check if the user has a UserProfile object, and create one if not.
    """
    if not hasattr(user, 'userprofile'):
        UserProfile.objects.create(user=user)


@receiver(user_signed_up)  # Signal is sent when a user signs up
def create_user_profile(sender, request, user, **kwargs):
    """
    Create a UserProfile object for the user upon signup.
    """
    UserProfile.objects.create(user=user)


@receiver(user_logged_in)  # Signal is sent when a user logs in
def check_suspicious_activity(sender, request, user, **kwargs):
    """
    Grabs the user's ip-address, geolocates it, and checks if the user's last known country is different from the current
    country. If it is, an email is sent to the user notifying them of the suspicious activity.
    :param sender:
    :param request:
    :param user:
    :param kwargs:
    :return:
    """
    profile, created = UserProfile.objects.get_or_create(user=user)

    current_ip = get_client_ip(request)  # Get ip from request

    location_data = get_geoip_data(current_ip)  # Get location data from ip
    current_country = location_data['country']

    # Set the context for the email
    context = {
        'user': user,
        'ip_address': current_ip,
        'city': location_data['city'],
        'country': current_country,
    }

    # If the user has a last known country, and it is different from the current country, send an email
    if profile.last_known_country and profile.last_known_country != current_country:
        message = render_to_string('emails/suspicious_activity.html', context)
        send_mail(
            'Suspicious Login Attempt',
            message,
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )

        # Update the user's last known country
        profile.last_known_country = current_country
        profile.save()








