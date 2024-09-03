import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from allauth.account.models import EmailAddress
from django.contrib.sessions.models import Session
from django.utils import timezone
from main.models import Account, Transaction, Item
import random
from main.forms import CreateAccountForm
from django.http import JsonResponse
import json


def create_user(client):
    User = get_user_model()
    user = User.objects.create_user(username='testuser', password='password', email='testuser@example.com')
    EmailAddress.objects.create(user=user, email=user.email, primary=True, verified=True)
    client.login(username='testuser', password='password')
    return user


def set_session_info(client):
    session = client.session
    session['session_info_stored'] = True
    session.save()


def create_account(client, user):
    account = Account.objects.create(
        user=user,
        name='Test Account',
        account_type='checking',
        balance=1000
    )
    return account


def create_transactions(client, n, account, transaction_type):
    for i in range(n):
        Transaction.objects.create(
            account=account,
            transaction_type=transaction_type,
            amount=random.randint(1, 1000),
            date='2024-01-01',
            description=f'Test Description {i}'
        )


@pytest.mark.django_db
def test_new_manual_transaction(client):
    user = create_user(client)
    set_session_info(client)

    account = create_account(client, user)

    url = reverse('new_transaction', kwargs={'account_name': account.name})

    # Test GET request
    response = client.get(url)
    assert response.status_code == 200
    assert 'transactions/new_transaction.html' in [t.name for t in response.templates]
    # Make sure the form is in the context
    assert 'form' in response.context

    transaction_types = ['deposit', 'withdrawal', 'payment']

    for t_type in transaction_types:
        before_balance = account.balance
        amount = random.randint(1, 100)
        date = '2024-01-01'
        data = {
            'transaction_type': t_type,
            'amount': amount,
            'description': f'Test Description for {t_type}',
            'date': date
        }
        response = client.post(url, data)
        assert response.status_code == 302
        # Check that the transaction was created
        assert Transaction.objects.filter(amount=amount, date=date, transaction_type=t_type, description=f'Test Description for {t_type}').exists()
        # Check that the account balance was updated
        account.refresh_from_db()
        if t_type == 'deposit':
            assert account.balance == before_balance + amount
        else:
            assert account.balance == before_balance - amount

    # Test transfer_to functionality
    # Create a second account
    transfer_account1 = Account.objects.create(
        user=user,
        name='Transfer Account 1',
        account_type='checking',
        balance=1000
    )
    transfer_url = reverse('new_transaction', kwargs={'account_name': transfer_account1.name})
    # Create a second account
    transfer_account2 = Account.objects.create(
        user=user,
        name='Transfer Account 2',
        account_type='checking',
        balance=1000
    )
    # Create a transfer transaction and send to Test Account 2
    data = {
        'transaction_type': 'transfer',
        'amount': 100,
        'description': 'Test Description',
        'date': '2024-01-01',
        'transfer_to': transfer_account2.pk
    }
    response = client.post(transfer_url, data)
    assert response.status_code == 302
    # Check that the transaction was created
    assert Transaction.objects.filter(account=transfer_account1, amount=100, date='2024-01-01', transaction_type='transfer', description='Test Description').exists()
    assert Transaction.objects.filter(account=transfer_account2, amount=100, transaction_type='deposit', description='Transfer from Transfer Account 1').exists()
    # Check that the account balances were updated
    transfer_account1.refresh_from_db()
    transfer_account2.refresh_from_db()
    assert transfer_account1.balance == 900
    assert transfer_account2.balance == 1100


@pytest.mark.django_db
def test_transaction_details(client):
    user = create_user(client)
    set_session_info(client)

    account = create_account(client, user)

    new_purchase_transaction = Transaction.objects.create(
        account=account,
        transaction_type='purchase',
        amount=100,
        date='2024-01-01',
        description='Test Description'
    )
    new_item = Item.objects.create(
        transaction=new_purchase_transaction,
        description='Test Item',
        price=100,
        quantity=1
    )
    new_item.save()
    new_purchase_transaction.save()

    url = reverse('transaction_detail', kwargs={'pk': new_purchase_transaction.pk})
    response = client.get(url)
    assert response.status_code == 200

    assert 'transactions/transaction_detail.html' in [t.name for t in response.templates]
    assert 'transaction' in response.context
    assert 'items' in response.context
    assert response.context['transaction'] == new_purchase_transaction

    # Test POST request
    data = {
        'include_in_statistics': False
    }
    response = client.post(url, data)
    assert response.status_code == 302
    assert Transaction.objects.get(pk=new_purchase_transaction.pk).include_in_statistics == False


@pytest.mark.django_db
def test_delete_transaction_purchase(client):
    user = create_user(client)
    set_session_info(client)

    account = create_account(client, user)

    new_purchase_transaction = Transaction.objects.create(
        account=account,
        transaction_type='purchase',
        amount=100,
        date='2024-01-01',
        description='Test Purchase'
    )
    new_item = Item.objects.create(
        transaction=new_purchase_transaction,
        description='Test Item',
        price=100,
        quantity=1
    )

    url = reverse('delete_transaction', kwargs={'pk': new_purchase_transaction.pk})
    response = client.post(url)

    # Check redirection
    assert response.status_code == 302
    assert response.url == reverse('account_details', kwargs={'account_name': account.name})

    # Check transaction deletion
    assert not Transaction.objects.filter(pk=new_purchase_transaction.pk).exists()

    # Check item deletion
    assert not Item.objects.filter(pk=new_item.pk).exists()

    # Check account balance update
    account.refresh_from_db()
    assert account.balance == 1100  # Reverted balance after deleting the purchase


@pytest.mark.django_db
def test_delete_transaction_deposit(client):
    user = create_user(client)
    set_session_info(client)

    account = create_account(client, user)

    new_deposit_transaction = Transaction.objects.create(
        account=account,
        transaction_type='deposit',
        amount=200,
        date='2024-01-01',
        description='Test Deposit'
    )

    url = reverse('delete_transaction', kwargs={'pk': new_deposit_transaction.pk})
    response = client.post(url)

    # Check redirection
    assert response.status_code == 302
    assert response.url == reverse('account_details', kwargs={'account_name': account.name})

    # Check transaction deletion
    assert not Transaction.objects.filter(pk=new_deposit_transaction.pk).exists()

    # Check account balance update
    account.refresh_from_db()
    assert account.balance == 800  # Reverted balance after deleting the deposit


@pytest.mark.django_db
def test_delete_transaction_transfer(client):
    user = create_user(client)
    set_session_info(client)

    account_from = create_account(client, user)

    account_to = create_account(client, user)

    transfer_transaction = Transaction.objects.create(
        account=account_from,
        transaction_type='transfer',
        amount=300,
        date='2024-01-01',
        description='Transfer to Savings',
        transfer_to=account_to
    )

    # Simulate corresponding deposit in the destination account
    corresponding_deposit = Transaction.objects.create(
        account=account_to,
        transaction_type='deposit',
        amount=300,
        date='2024-01-01',
        description=f'Transfer from {account_from.name}'
    )

#  Next thing I need to do is to test the Azure document intelligence integration






