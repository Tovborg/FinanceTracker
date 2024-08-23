from allauth.account.signals import user_logged_in, user_signed_up
from django.dispatch import receiver
from main.models import UserProfile
from .utils.utils import get_client_ip, get_geoip_data
from django.core.mail import send_mail
from django.conf import settings

# User profile signals


@receiver(user_logged_in)
def check_user_profile(sender, request, user, **kwargs):
    """
    Check if the user has a UserProfile object, and create one if not.
    """
    if not hasattr(user, 'userprofile'):
        UserProfile.objects.create(user=user)


@receiver(user_signed_up)
def create_user_profile(sender, request, user, **kwargs):
    """
    Create a UserProfile object for the user upon signup.
    """
    UserProfile.objects.create(user=user)


@receiver(user_logged_in)
def check_suspicious_activity(sender, request, user, **kwargs):
    profile, created = UserProfile.objects.get_or_create(user=user)

    current_ip = get_client_ip(request)

    location_data = get_geoip_data(current_ip)
    current_country = location_data['country']

    if profile.last_known_country and profile.last_known_country != current_country:
        send_mail(
            'Suspicious Login Attempt',
            f'We detected a login from a new location: {location_data["city"]}, {location_data["country"]}.'
            f' If this was you, you can ignore this message. If not, please change your password immediately.'
            f'IP address: {current_ip}',
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )

        profile.last_known_country = current_country
        profile.save()








