from allauth.usersessions.adapter import DefaultUserSessionsAdapter


class CustomUserSessionsAdapter(DefaultUserSessionsAdapter):
    def get_user_sessions(self, request):
        sessions = super().get_user_sessions(request)
        return sessions

    def terminate_session(self, request, session_key):
        return super().terminate_session(request, session_key)