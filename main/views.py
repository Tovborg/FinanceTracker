from django.shortcuts import render, redirect, get_object_or_404
from main.forms import RegistrationForm, CreateAccountForm, NewTransactionForm
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from main.models import Account, Transaction
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import datetime
from django.contrib import messages


# Use @login_required decorator to ensure only authenticated users can access the view

@login_required
def index(request):
    accounts = Account.objects.filter(user=request.user)
    favorites = Account.objects.filter(user=request.user, isFavorite=True)
    three_recent_transactions = Transaction.objects.filter(account__user=request.user).order_by('-date')[:3]
    current_date = datetime.date.today()
    total_expenses = 0
    total_income = 0
    for account in accounts:
        total_expenses += account.get_monthly_expenses()
    # Dashboard info
    for account in accounts:
        total_income += account.get_monthly_income()
    total_balance = sum([account.balance for account in accounts])
    no_accounts = len(accounts)
    if len(accounts) > 3:
        accounts = accounts[:3]

    if len(favorites) > 3:
        favorites = favorites[:3]
    favorites_count = len(favorites)

    context = {"accounts": accounts,
               "total_balance": total_balance,
               "no_accounts": no_accounts,
               'total_expenses': total_expenses,
               'total_income': total_income,
               'current_date': current_date}

    if favorites_count == 0:
        print('No favorites')
        return render(request, "dashboard.html", context=context)
    elif favorites_count < 3:
        # Fetch additional non-favorite accounts to make up the count to 3
        additional_accounts = Account.objects.filter(user=request.user, isFavorite=False)[:3 - favorites_count]
        combined_accounts = list(favorites) + list(additional_accounts)
        return render(request, "dashboard.html", context=context)

    else:
        print(favorites)
        return render(request, "dashboard.html", context=context)


def sign_up(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('/')
    else:
        form = RegistrationForm()
    return render(request, "registration/signup.html", {"form": form})


# Views to display and handle accounts
@login_required
def account_view(request):
    user_accounts = Account.objects.filter(user=request.user)
    return render(request, "account/account.html", context={"accounts": user_accounts})


@login_required
def account_info(request, account_name):
    account = get_object_or_404(Account, name=account_name, user=request.user)
    return render(request, "account/account_info.html", context={"account": account})


@require_POST
@login_required
def delete_account(request, account_name):
    account = get_object_or_404(Account, name=account_name, user=request.user)
    # Delete transactions associated with the account
    account.transaction_set.all().delete()
    account.delete()
    return redirect('account')


@login_required
def account_details(request, account_name):
    account = get_object_or_404(Account, name=account_name, user=request.user)
    transactions_list = account.transaction_set.all().order_by('-date')

    paginator = Paginator(transactions_list, 5)
    page_number = request.GET.get('page')
    try:
        transactions = paginator.page(page_number)
    except PageNotAnInteger:
        transactions = paginator.page(1)
    except EmptyPage:
        transactions = paginator.page(paginator.num_pages)

    return render(request, "account/account_details.html", context={"account": account, "transactions": transactions})


@login_required
def add_account(request):
    if request.method == "POST":
        form = CreateAccountForm(request.POST)
        if form.is_valid():
            print(form.errors)
            print(form.cleaned_data)
            # Create a new account
            account_name = form.cleaned_data['account_name']
            account_balance = form.cleaned_data['account_balance']
            account_type = form.cleaned_data['account_type']
            account_number = form.cleaned_data['account_number']
            description = form.cleaned_data['description']

            new_account = Account(
                user=request.user,
                name=account_name,
                balance=account_balance,
                account_type=account_type,
                description=description,
                account_number=account_number
            )
            new_account.save()
            return redirect('account')
    else:
        form = CreateAccountForm()
    return render(request, "account/add_account.html", {"form": form})

@login_required
@require_POST
def edit_account(request, account_name, field):
    account = get_object_or_404(Account, name=account_name, user=request.user)
    new_value = request.POST.get('new_value')
    print(new_value)
    if new_value is None:
        messages.error(request, 'New value cannot be empty')
        return redirect('account_info', account_name=account_name)
    if new_value is '':
        messages.error(request, 'New value cannot be empty')
        return redirect('account_info', account_name=account_name)

    valid_fields = ['name', 'account_number', 'account_type']
    if field in valid_fields:
        print('Valid field')
        setattr(account, field, new_value)
        account.save()
        messages.success(request, f'{field.replace("_", " ").capitalize()} updated successfully.')
    else:
        messages.error(request, 'Invalid field.')
    if field == 'name':
        if new_value:
            account_name = new_value
        else:
            account_name = account.name
    return redirect('account_info', account_name=account_name)


@require_POST
@login_required
def updateFavorite(request):
    account_name = request.POST.get('account_name')
    print(request)
    account = Account.objects.get(name=account_name)
    account.isFavorite = not account.isFavorite
    account.save()
    return JsonResponse({'status': 'ok'})


@login_required
def new_transaction(request, account_name):
    account = get_object_or_404(Account, name=account_name, user=request.user)
    accounts = Account.objects.filter(user=request.user).exclude(name=account_name)
    if request.method == "POST":
        form = NewTransactionForm(request.POST, user=request.user)
        if form.is_valid():
            print('form is valid')
            transaction_type = form.cleaned_data['transaction_type']
            amount = form.cleaned_data['amount']
            date = form.cleaned_data['date']
            description = form.cleaned_data['description']
            transfer_to = form.cleaned_data['transfer_to']

            # Calculate balance after transaction
            if transaction_type == 'deposit':
                balance_after = account.balance + amount
            elif transaction_type == 'withdrawal':
                balance_after = account.balance - amount
            elif transaction_type == 'transfer' and transfer_to:
                balance_after = account.balance - amount
            else:
                balance_after = account.balance

            transaction = Transaction(
                account=account,
                transaction_type=transaction_type,
                amount=amount,
                date=date,
                description=description,
                transfer_to=transfer_to,
                balance_after=balance_after
            )
            transaction.save()

            handleTransaction(transaction_type, amount, account, transfer_to, transaction)
            return redirect('account_details', account_name=account_name)
        else:
            print(form.errors)
    else:
        form = NewTransactionForm(user=request.user)
    return render(request, "new_transaction.html", context={"account": account, "form": form, "accounts": accounts})


# Needs new logic to handle insufficient funds
def handleTransaction(transaction_type, amount, account, transfer_to, transaction):
    if transaction_type == 'deposit':
        account.balance += amount
    elif transaction_type == 'withdrawal':
        account.balance -= amount
    elif transaction_type == 'transfer' and transfer_to:
        account.balance -= amount
        transfer_to.balance += amount
        transfer_to.save()
        receiver_transaction = Transaction(
            account=transfer_to,
            transaction_type='deposit',
            amount=amount,
            date=transaction.date,
            description=f"Transfer from {account.name}",
            balance_after=transfer_to.balance
        )
        receiver_transaction.save()
    account.save()
    transaction.balance_after = account.balance
    transaction.save()


