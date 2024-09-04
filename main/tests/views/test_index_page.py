import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from main.models import Paychecks, Account, Transaction
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.utils import timezone
from allauth.account.models import EmailAddress
import datetime

def create_user(client):
    User = get_user_model()
    user = User.objects.create_user(
        username='testuser',
        password='password',
        email='testuser@example.com'
    )
    EmailAddress.objects.create(
        user=user, email=user.email, primary=True, verified=True
    )
    client.login(username='testuser', password='password')
    return user


def set_session_info(client):
    session = client.session
    session['session_info_stored'] = True
    session.save()


@pytest.mark.django_db
def test_index_page(client):
    user = create_user(client)
    set_session_info(client)

    # Create accounts for the user
    for i in range(6):
        Account.objects.create(
            user=user,
            name=f'Test Account {i}',
            account_type='checking',
            balance=1000,
            isFavorite=False if i % 2 == 0 else True
        )

    response = client.get(reverse('index'))
    assert response.status_code == 200

    favorite_accounts = Account.objects.filter(user=user, isFavorite=True)
    non_favorite_accounts = Account.objects.filter(user=user, isFavorite=False)

    for account in favorite_accounts:
        assert account.name.encode() in response.content
        assert str(account.balance) in response.content.decode()




