# middleware.py

from django.utils import timezone
from django.contrib.sessions.models import Session
from django_user_agents.utils import get_user_agent
from .utils.utils import get_geoip_data


class ActiveUserSessionMiddleware:
    """
    Middleware to store device and browser information in the session upon login.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.user.is_authenticated and not request.session.get('session_info_stored'):
            user_agent = get_user_agent(request)
            location_data = get_geoip_data(self.get_client_ip(request))
            session_data = {
                'ip_address': self.get_client_ip(request),
                'device': self.get_device_type(user_agent),
                'browser': user_agent.browser.family,
                'browser_version': user_agent.browser.version_string,
                'os': user_agent.os.family,
                'os_version': user_agent.os.version_string,
                'device_type': self.get_device_type(user_agent),
                'login_time': timezone.now().isoformat(),
                # Location data
                'country': location_data['country'],
                'city': location_data['city'],
                'latitude': location_data['latitude'],
                'longitude': location_data['longitude'],
                # 'time_zone': location_data['time_zone'],
            }
            request.session['session_info'] = session_data
            request.session['session_info_stored'] = True  # To prevent updating the session data on every request

        return response

    @staticmethod
    def get_client_ip(request):
        """
        Retrieve the client's IP address from the request object.
        :param request:
        :return: ip_address
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    @staticmethod
    def get_device_type(user_agent):
        """
        Retrieve the client's device type from the request object.
        :param request:
        :return: device_type
        """
        if user_agent.is_mobile:
            return 'Mobile'
        elif user_agent.is_tablet:
            return 'Tablet'
        elif user_agent.is_pc:
            return 'PC'
        elif user_agent.is_bot:
            return 'Bot'
        else:
            return 'Unknown'