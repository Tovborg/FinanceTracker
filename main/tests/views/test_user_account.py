import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from allauth.account.models import EmailAddress
from django.contrib.sessions.models import Session
from django.utils import timezone


def create_user(client):
    User = get_user_model()
    user = User.objects.create_user(username='testuser', password='password', email='testuser@example.com')
    EmailAddress.objects.create(user=user, email=user.email, primary=True, verified=True)
    return user


@pytest.mark.django_db
def test_delete_user_view(client):
    # Create a user
    user = create_user(client)

    # Login the user
    client.login(username='testuser', password='password')

    # Set session_info_stored to avoid middleware error
    session = client.session
    session['session_info_stored'] = True
    session.save()

    # Send a POST request to delete the user
    delete_url = reverse('delete_user')
    response = client.post(delete_url)

    # Check that the user is redirected to the login page
    assert response.status_code == 302
    assert response.url == reverse('account_login')

    # Check that the user is deleted
    assert User.objects.filter(username='testuser').count() == 0


@pytest.mark.django_db
def test_custom_security_index_view(client):
    # Create a user
    user = create_user(client)

    # Login the user
    client.login(username='testuser', password='password')

    # Set session_info_stored to avoid middleware error
    session = client.session
    session['session_info_stored'] = True
    session.save()

    url = reverse('mfa_index')
    response = client.get(url)

    assert response.status_code == 200

    assert 'mfa/index.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_terminate_all_sessions_view(client):
    # Create a user
    user = create_user(client)

    # Login the user
    client.login(username='testuser', password='password')

    # Simulate the creation of a session for the user
    session = client.session
    session['_auth_user_id'] = str(user.id)
    session.save()

    assert Session.objects.filter(expire_date__gte=timezone.now(), session_key=session.session_key).exists()

    url = reverse('terminate_all_sessions')
    response = client.post(url)

    assert response.status_code == 302
    assert response.url == reverse('account_login')

    assert not Session.objects.filter(expire_date__gte=timezone.now(), session_key=session.session_key).exists()


@pytest.mark.django_db
def test_user_info_view(client):
    # create user
    user = create_user(client)
    # set user specific info
    user.first_name = 'John'
    user.last_name = 'Doe'
    user.save()
    # login user
    client.login(username='testuser', password='password')
    # Set session_info_stored to avoid middleware error
    session = client.session
    session['session_info_stored'] = True
    session.save()

    url = reverse('user_info') # get url
    response = client.get(url)
    # check response status code
    assert response.status_code == 200
    # check if user info is displayed
    assert 'John' in response.content.decode()
    assert 'Doe' in response.content.decode()
    assert 'testuser' in response.content.decode()
    assert 'testuser@example.com' in response.content.decode()
    assert 'account/user_account_details.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_terminate_session_view(client):
    # create use
    user = create_user(client)
    # login user
    client.login(username='testuser', password='password')
    # Create first sessions
    session1 = client.session
    session1['_auth_user_id'] = str(user.id)
    session1.save()

    session1.create()
    session1.save()

    # Create second session
    client.logout()
    client.login(username='testuser', password='password')
    session2 = client.session
    session2['_auth_user_id'] = str(user.id)
    session2.save()

    session2.create()
    session2.save()

    # Check that both sessions exist
    assert Session.objects.filter(session_key=session1.session_key).exists()
    assert Session.objects.filter(session_key=session2.session_key).exists()

    # POST request to terminate the first session
    url = reverse('terminate_session', kwargs={'session_key': session1.session_key})
    response = client.post(url)

    assert response.status_code == 302
    assert response.url == reverse('mfa_index')

    # Check that the first session is terminated
    assert not Session.objects.filter(session_key=session1.session_key).exists()
    # Check that the second session still exists
    assert Session.objects.filter(session_key=session2.session_key).exists()



