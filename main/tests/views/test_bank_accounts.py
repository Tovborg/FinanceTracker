import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from allauth.account.models import EmailAddress
from django.contrib.sessions.models import Session
from django.utils import timezone
from main.models import Account
import random
from main.forms import CreateAccountForm
from django.http import JsonResponse
import json
import requests

# Create a user
def create_user(client):
    User = get_user_model()
    user = User.objects.create_user(username='testuser', password='password', email="testuser@example.com")
    EmailAddress.objects.create(user=user, email=user.email, primary=True, verified=True)
    return user


# Create test environment functions
def create_accounts(client, n):
    # Grab the user
    user = User.objects.get(username='testuser')

    # Create n accounts
    for i in range(n):
        Account.objects.create(
            user=user,
            name=f"Account {i}",
            account_type=random.choice(['savings', 'checking', 'Vacation', 'Retirement', 'Other']),
            balance=random.randint(0, 10000),
            description=f"Description {i}",
            isFavorite=random.choice([True, False]),
        )

    return user


@pytest.mark.django_db
def test_accounts_view(client):
    """
    This test checks that the accounts view is rendered correctly
    :param client:
    :return:
    """
    # Create a user
    user = create_user(client)
    # Login the user
    client.login(username='testuser', password='password')
    # Set session_info_stored to avoid middleware error
    session = client.session
    session['session_info_stored'] = True
    session.save()

    # Create 5 accounts
    create_accounts(client, 5)

    # Send a GET request to the accounts view
    url = reverse('account')
    response = client.get(url)

    # Check that the response is successful
    assert response.status_code == 200

    # Check that the user has 5 accounts
    assert Account.objects.filter(user=user).count() == 5

    # Check that the user has 5 accounts in the context
    assert len(response.context['accounts']) == 5

    # Check that the all 5 accounts are rendered and make sure relevant information is displayed
    for account in response.context['accounts']:
        assert account.name in response.content.decode()
        assert str(account.balance) in response.content.decode()


@pytest.mark.django_db
def test_add_account_view_get(client):
    """
    This test checks that the add account view is rendered correctly
    :param client:
    :return:
    """
    user = create_user(client)  # Create a user
    client.login(username='testuser', password='password')

    # Set session_info_stored to avoid middleware error
    session = client.session
    session['session_info_stored'] = True
    session.save()

    url = reverse('add_account')  # Get url
    response = client.get(url)  # Send a GET request to the add account view

    # Check that the response is successful
    assert response.status_code == 200
    # Check template used
    assert 'bank_accounts/add_account.html' in [t.name for t in response.templates]
    # check that the form is in the context
    assert isinstance(response.context['form'], CreateAccountForm)


@pytest.mark.django_db
def test_add_account_view_post_valid_data(client):
    """
    This test checks that the add account view handles valid form data correctly and creates a new account
    :param client:
    :return
    """
    user = create_user(client)  # Create a user
    client.login(username='testuser', password='password')

    # Set session_info_stored to avoid middleware error
    session = client.session
    session['session_info_stored'] = True
    session.save()

    url = reverse('add_account')  # Get url

    # Create data for the form
    data = {
        'account_name': 'Test Account',
        'account_balance': 1000.00,
        'account_type': 'savings',
        'description': 'Test Description',
        'account_number': '1234567890',
    }
    response = client.post(url, data)  # Send a POST request to the add account view with the form data

    # Check that the account was created
    assert Account.objects.filter(user=user, name='Test Account').exists()
    # Check that the user is redirected to the accounts page
    assert response.status_code == 302
    assert response.url == reverse('account')


@pytest.mark.django_db
def test_add_account_view_post_invalid_data(client):
    """
    This test checks that the add account view handles invalid form data correctly
    :param client:
    :return
    """
    # Create a user and log them in
    user = create_user(client)
    client.login(username='testuser', password='password')

    # Make a POST request with invalid data (e.g., missing required fields)
    url = reverse('add_account')
    data = {
        'account_name': '',  # Missing account name
        'account_balance': 1000.00,
        'account_type': 'Savings',
        'description': 'Test Description',
        'account_number': '123456789'
    }
    response = client.post(url, data)

    # Check that the account was not created
    assert Account.objects.filter(user=user).count() == 0
    # Check that the form was not valid and re-rendered
    assert response.status_code == 200
    assert 'bank_accounts/add_account.html' in [t.name for t in response.templates]
    # Check that the errors are in the form
    assert 'This field is required.' in str(response.content)


@pytest.mark.django_db
def test_account_details_view(client):
    user = create_user(client)
    client.login(username='testuser', password='password')

    session = client.session
    session['session_info_stored'] = True
    session.save()

    account = Account.objects.create(
        user=user,
        name='Test Account',
        account_type='savings',
        balance=1000.00,
        description='Test Description',
        account_number='1234567890',
    )

    assert Account.objects.filter(user=user, name='Test Account').exists()

    url = reverse('account_details', args=[account.name])
    response = client.get(url)

    assert response.status_code == 200
    assert 'bank_accounts/account_details.html' in [t.name for t in response.templates]

    assert response.context['account'] == account
    # Check that the account details are rendered
    assert account.name in response.content.decode()
    assert str(int(account.balance)) in response.content.decode()
    assert account.account_number in response.content.decode()


@pytest.mark.django_db
def test_account_info_view(client):
    user = create_user(client)
    client.login(username='testuser', password='password')

    session = client.session
    session['session_info_stored'] = True
    session.save()

    account = Account.objects.create(
        user=user,
        name='Test Account',
        account_type='savings',
        balance=1000.00,
        description='Test Description',
        account_number='1234567890',
    )

    assert Account.objects.filter(user=user, name='Test Account').exists()

    url = reverse('account_info', args=[account.name])
    response = client.get(url)

    assert response.status_code == 200
    assert 'bank_accounts/account_info.html' in [t.name for t in response.templates]

    assert response.context['account'] == account
    # Check that the account details are rendered
    assert account.name in response.content.decode()
    assert str(int(account.balance)) in response.content.decode()
    assert account.account_number in response.content.decode()
    assert str(account.accumulated_interest) in response.content.decode()
    assert account.account_type in response.content.decode()


@pytest.mark.django_db
def test_account_delete_view(client):
    user = create_user(client)
    client.login(username='testuser', password='password')

    session = client.session
    session['session_info_stored'] = True
    session.save()

    account = Account.objects.create(
        user=user,
        name='Test Account',
        account_type='savings',
        balance=1000.00,
        description='Test Description',
        account_number='1234567890',
    )

    assert Account.objects.filter(user=user, name='Test Account').exists()

    url = reverse('delete_account', args=[account.name])
    response = client.post(url)

    assert not Account.objects.filter(user=user, name='Test Account').exists()
    assert response.status_code == 302
    assert response.url == reverse('account')


@pytest.mark.django_db
def test_edit_account_view_valid_data(client):
    """
    This test checks that the edit account view handles valid form data correctly
    It checks that all fields can be edited and that the changes are saved
    :param client:
    :return:
    """
    user = create_user(client)
    client.login(username='testuser', password='password')

    session = client.session
    session['session_info_stored'] = True
    session.save()

    account = Account.objects.create(
        user=user,
        name='Test Account',
        account_type='savings',
        balance=1000.00,
        description='Test Description',
        account_number='1234567890',
    )

    assert Account.objects.filter(user=user, name='Test Account').exists()

    url = reverse('edit_account', args=[account.name, 'name'])

    data = {
        'new_value': 'New Account Name'
    }

    response = client.post(url, data)

    account.refresh_from_db()  # Refresh the account from the database

    assert response.status_code == 302
    assert response.url == reverse('account_info', args=[account.name])
    assert account.name == 'New Account Name'

    url = reverse('edit_account', args=[account.name, 'accumulated_interest'])
    data = {
        'new_value': 100.00
    }
    response = client.post(url, data)
    account.refresh_from_db()
    assert response.status_code == 302
    assert response.url == reverse('account_info', args=[account.name])

    assert account.accumulated_interest == 100.00

    url = reverse('edit_account', args=[account.name, 'account_number'])
    data = {
        'new_value': '9876543210'
    }
    response = client.post(url, data)
    account.refresh_from_db()
    assert response.status_code == 302
    assert response.url == reverse('account_info', args=[account.name])
    assert account.account_number == '9876543210'

    url = reverse('edit_account', args=[account.name, 'account_type'])
    data = {
        'new_value': 'checking'
    }
    response = client.post(url, data)
    account.refresh_from_db()
    assert response.status_code == 302
    assert response.url == reverse('account_info', args=[account.name])
    assert account.account_type == 'checking'


@pytest.mark.django_db
def test_edit_account_view_invalid_data(client):
    """
    This test checks that the edit account view handles invalid form data correctly
    :param client:
    :return
    """
    user = create_user(client)
    client.login(username='testuser', password='password')

    session = client.session
    session['session_info_stored'] = True
    session.save()

    account1 = Account.objects.create(
        user=user,
        name='Test Account 1',
        account_type='savings',
        balance=1000.00,
        description='Test Description',
        account_number='1234567890',
    )
    account2 = Account.objects.create(
        user=user,
        name='Test Account 2',
        account_type='savings',
        balance=1000.00,
        description='Test Description',
        account_number='1234567890',
    )

    assert Account.objects.filter(user=user, name='Test Account 1').exists()
    assert Account.objects.filter(user=user, name='Test Account 2').exists()

    url = reverse('edit_account', args=[account1.name, 'name'])
    # Try to change the name to the name of another account
    data = {
        'new_value': 'Test Account 2'
    }
    response = client.post(url, data)
    account1.refresh_from_db()
    assert response.status_code == 302
    assert response.url == reverse('account_info', args=[account1.name])
    assert account1.name == 'Test Account 1'  # Check that the name was not changed
    # Try to change the name to an empty string
    data = {
        'new_value': ''
    }
    response = client.post(url, data)
    account1.refresh_from_db()
    assert response.status_code == 302
    assert account1.name == 'Test Account 1'  # Check that the name was not changed
    #
    url = reverse('edit_account', args=[account1.name, 'account_type'])
    # Try to change the account type to an invalid value
    data = {
        'new_value': 'invalid'
    }
    response = client.post(url, data)
    account1.refresh_from_db()
    assert response.status_code == 302
    assert account1.account_type == 'savings'  # Check that the account type was not changed
















