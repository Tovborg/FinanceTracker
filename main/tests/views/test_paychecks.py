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


def create_paycheck(client, user, status, account, ):
    paycheck = Paychecks.objects.create(
        user=user,
        amount=1000,
        payout_account=account,
        pay_date='2024-02-01',
        pay_period_start='2024-01-01',
        pay_period_end='2024-01-15',
        employer='Test Employer',
        status=status,
        description='Test Description'
    )
    return paycheck


@pytest.mark.django_db
def test_paycheck_list_view(client):
    user = create_user(client)
    set_session_info(client)

    account = Account.objects.create(
        user=user,
        name='Test Account',
        account_type='checking',
        balance=1000
    )
    # Create 6 paychecks
    for i in range(6):
        create_paycheck(client, user, 'paid', account)

    paychecks = Paychecks.objects.all()
    assert paychecks.count() == 6

    url = reverse('paychecks')
    response = client.get(url)
    assert response.status_code == 200

    # make sure there's only 5 paychecks on the page
    assert len(response.context['page_obj']) == 5
    assert response.context['page_obj'].paginator.count == 6

    # check template used
    assert 'paychecks/paychecks.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_paycheck_list_view_no_paychecks(client):
    user = create_user(client)
    set_session_info(client)

    account = Account.objects.create(
        user=user,
        name='Test Account',
        account_type='checking',
        balance=1000
    )

    url = reverse('paychecks')
    response = client.get(url)
    assert response.status_code == 200

    # make sure it uses the no_paychecks_error.html template
    assert 'paychecks/no_paychecks_error.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_add_paycheck_get(client):
    user = create_user(client)
    set_session_info(client)

    account = Account.objects.create(
        user=user,
        name='Test Account',
        account_type='checking',
        balance=1000
    )

    url = reverse('add_paycheck')
    response = client.get(url)
    assert response.status_code == 200
    assert 'paychecks/add_paycheck.html' in [t.name for t in response.templates]


@pytest.mark.django_db
def test_add_paycheck_post_valid(client):
    user = create_user(client)
    set_session_info(client)

    account = Account.objects.create(
        user=user,
        name='Test Account',
        account_type='checking',
        balance=1000
    )

    url = reverse('add_paycheck')
    data = {
        'amount': 1000,
        'pay_date': '2024-02-01',
        'start_pay_period': '2024-01-01',
        'end_pay_period': '2024-01-15',
        'payout_account': account.id,
        'employer': 'Test Employer',
        'status': 'paid',
        'description': 'Test Description'
    }
    response = client.post(url, data)
    # check response is redirect and paycheck is created
    assert response.status_code == 302
    assert Paychecks.objects.count() == 1
    # Test that a transaction is created on the account
    assert Transaction.objects.count() == 1
    # make sure the paycheck information is stored correctly
    paycheck = Paychecks.objects.first()
    assert paycheck.amount == 1000
    assert paycheck.payout_account == account
    assert str(paycheck.pay_date) == '2024-02-01'
    assert str(paycheck.pay_period_start) == '2024-01-01'
    assert str(paycheck.pay_period_end) == '2024-01-15'
    assert paycheck.employer == 'Test Employer'
    assert paycheck.status == 'paid'
    assert paycheck.description == 'Test Description'


@pytest.mark.django_db
def test_add_paycheck_post_invalid(client):
    user = create_user(client)
    set_session_info(client)

    account = Account.objects.create(
        user=user,
        name='Test Account',
        account_type='checking',
        balance=1000
    )

    url = reverse('add_paycheck')
    data = {
        'pay_date': '2024-02-01',
        'start_pay_period': '2024-01-01',
        'end_pay_period': '2024-01-15',
        'payout_account': account.id,
        'employer': 'Test Employer',
        'status': 'paid',
        'description': 'Test Description'
    }
    response = client.post(url, data)
    # check response is not redirect and paycheck is not created
    assert response.status_code == 200
    assert Paychecks.objects.count() == 0
    # make sure the form is returned with errors
    assert 'paychecks/add_paycheck.html' in [t.name for t in response.templates]
    assert response.context['form'].errors == {
        'amount': ['This field is required.']
    }

    data = {
        'amount': 1000,
        'pay_date': '2024-02-01',
        'start_pay_period': '2024-01-16',
        'end_pay_period': '2024-01-15',
        'payout_account': account.id,
        'employer': 'Test Employer',
        'status': 'paid',
        'description': 'Test Description'
    }
    response = client.post(url, data)
    # check response is not redirect and paycheck is not created
    assert response.status_code == 200
    assert Paychecks.objects.count() == 0
    # make sure the form is returned with errors
    assert 'paychecks/add_paycheck.html' in [t.name for t in response.templates]
    assert response.context['form'].errors == {
        '__all__': ['End of pay period must be after start of pay period.']
    }

    data = {
        'amount': 1000,
        'pay_date': datetime.date.today(),
        'start_pay_period': '2024-01-01',
        'end_pay_period': '2024-01-15',
        'payout_account': account.id,
        'employer': 'Test Employer',
        'status': 'pending',
        'description': 'Test Description'
    }
    response = client.post(url, data)
    # check response is not redirect and paycheck is not created
    assert response.status_code == 200
    assert Paychecks.objects.count() == 0
    # make sure the form is returned with errors
    assert 'paychecks/add_paycheck.html' in [t.name for t in response.templates]
    assert response.context['form'].errors == {
        '__all__': ['Pay date must be in the future for pending paychecks.']
    }


@pytest.mark.django_db
def test_paycheck_details(client):
    user = create_user(client)
    set_session_info(client)

    account = Account.objects.create(
        user=user,
        name='Test Account',
        account_type='checking',
        balance=1000
    )

    paycheck = create_paycheck(client, user, 'paid', account)

    url = reverse('paycheck_info', args=[paycheck.id])
    response = client.get(url)
    assert response.status_code == 200
    assert 'paychecks/paycheck_info.html' in [t.name for t in response.templates]
    assert response.context['paycheck'] == paycheck


@pytest.mark.django_db
def test_paycheck_delete(client):
    user = create_user(client)
    set_session_info(client)

    account = Account.objects.create(
        user=user,
        name='Test Account',
        account_type='checking',
        balance=1000
    )

    paycheck = create_paycheck(client, user, 'paid', account)

    url = reverse('delete_paycheck', args=[paycheck.id])
    response = client.post(url)
    assert response.status_code == 302
    assert Paychecks.objects.count() == 0
    assert Paychecks.objects.filter(id=paycheck.id).count() == 0

    # test that the transaction is also deleted
    assert Transaction.objects.count() == 0
    assert account.balance == 1000  # make sure the balance is reset












