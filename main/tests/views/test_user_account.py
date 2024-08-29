from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.auth.models import User
from allauth.account.models import EmailAddress
from main.models import UserProfile


class DeleteUserViewTest(TestCase):
    def setUp(self):
        # Create and save the user
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpassword',
            email='testuser@example.com',
        )

        # Ensure the user profile is created and saved
        self.user_profile = UserProfile.objects.create(user=self.user)
        assert self.user_profile.pk is not None, "UserProfile was not saved properly"

        # Verify the user's email
        EmailAddress.objects.create(
            user=self.user,
            email=self.user.email,
            primary=True,
            verified=True,
        )

        # Manually authenticate the user
        self.client.force_login(self.user)

        response = self.client.post(delete_url)

        self.assertEqual(response.status_code, 302) # Check that the response is a redirect

        with self.assertRaises(get_user_model().DoesNotExist):
            get_user_model().objects.get(username='testuser')
