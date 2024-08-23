from allauth.account.signals import user_logged_in, user_signed_up
from django.dispatch import receiver
from django.contrib.auth.models import User
from main.models import UserProfile
from django.utils import timezone
from django.contrib.sessions.models import Session
from .utils.utils import get_client_ip, get_geoip_data


# User profile signals
#
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


# Set user's last known country upon login
# @receiver(user_logged_in)
# def set_last_known_country(sender, request, user, **kwargs):
#     """
#     Check if the user's last known country is set, and update it if not.
#     :param sender:
#     :param request:
#     :param user:
#     :param kwargs:
#     :return:
#     """
#     if user.userprofile.last_known_country:
#         print(f"Last known country for user {user.username} is already set to {user.userprofile.last_known_country}")
#         return  # If the user's last known country is already set, return
#
#     # Get the latest session for the user
#     sessions = Session.objects.filter(expire_date__gte=timezone.now())
#
#     # iterate over the user's sessions to find the one associated with the current user
#     user_sessions = []
#     for session in sessions:
#         session_data = session.get_decoded()
#         if session_data.get('_auth_user_id') == str(request.user.id):
#             session_info = session_data.get('session_info')
#             if isinstance(session_info, dict):
#                 user_sessions.append(
#                     {
#                         'session_key': session.session_key,
#                         'expire_date': session.expire_date,
#                         'ip_address': session_info.get('ip_address'),
#                         'device': session_info.get('device'),
#                         'browser': session_info.get('browser'),
#                         'os': session_info.get('os'),
#                         'login_time': session_info.get('login_time'),
#                         'country': session_info.get('country'),
#                         'city': session_info.get('city'),
#                         'latitude': session_info.get('latitude'),
#                         'longitude': session_info.get('longitude'),
#                     }
#                 )
#
#     # Set the user's last known country to the country from the latest session
#     if not user_sessions:
#         location_data = get_geoip_data(get_client_ip(request))
#         if location_data['country']:
#             print(f"No sessions found for user {user.username}. Setting last known country to {location_data['country']}")
#             user.userprofile.last_known_country = location_data['country']
#             user.userprofile.save()
#         return
#
#     # Sort the user's sessions by login time
#     sorted_sessions = sorted(user_sessions, key=lambda x: x['login_time'])
#
#     # # Get the latest session
#     latest_session = sorted_sessions[-1]
#
#     if latest_session['country']:
#         print(f"Setting last known country for user {user.username} to {latest_session['country']}")
#         user.userprofile.last_known_country = latest_session['country']
#         user.userprofile.save()
#     else:
#         location_data = get_geoip_data(get_client_ip(request))
#         if location_data['country']:
#             print(f"Could not find country in the latest session for user {user.username}. Setting last known country "
#                   f"to {location_data['country']}")
#             user.userprofile.last_known_country = location_data['country']
#             user.userprofile.save()
#         return









