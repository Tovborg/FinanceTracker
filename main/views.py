from django.shortcuts import render, redirect, get_object_or_404
from main.forms import RegistrationForm, CreateAccountForm, NewTransactionForm
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from main.models import Account, Transaction
from django.views.decorators.http import require_POST
from django.http import JsonResponse
# Use @login_required decorator to ensure only authenticated users can access the view


@login_required
def index(request):
    accounts = Account.objects.filter(user=request.user)
    favorites = Account.objects.filter(user=request.user, isFavorite=True)

    if len(accounts) > 3:
        accounts = accounts[:3]

    if len(favorites) > 3:
        favorites = favorites[:3]
    favorites_count = len(favorites)

    if favorites_count == 0:
        print('No favorites')
        return render(request, "dashboard.html", context={"accounts": accounts})
    elif favorites_count < 3:
        # Fetch additional non-favorite accounts to make up the count to 3
        additional_accounts = Account.objects.filter(user=request.user, isFavorite=False)[:3 - favorites_count]
        combined_accounts = list(favorites) + list(additional_accounts)
        return render(request, "dashboard.html", context={"accounts": combined_accounts})
    else:
        print(favorites)
        return render(request, "dashboard.html", context={"accounts": favorites})



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
def account_details(request, account_name):
    account = get_object_or_404(Account, name=account_name, user=request.user)
    return render(request, "account/account_details.html", context={"account": account})


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
            description = form.cleaned_data['description']

            new_account = Account(
                user=request.user,
                name=account_name,
                balance=account_balance,
                account_type=account_type,
                description=description
            )
            new_account.save()
            return redirect('account')
    else:
        form = CreateAccountForm()
    return render(request, "account/add_account.html", {"form": form})


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
    if request.method == "POST":
        form = NewTransactionForm(request.POST)
        if form.is_valid():
            transaction_type = form.cleaned_data['transaction_type']
            amount = form.cleaned_data['amount']
            date = form.cleaned_data['date']
            description = form.cleaned_data['description']

            transaction = Transaction(
                account=account,
                transaction_type=transaction_type,
                amount=amount,
                date=date,
                description=description
            )
            transaction.save()
            return redirect('account_details', account_name=account_name)
    form = NewTransactionForm()
    return render(request, "new_transaction.html", context={"account": account, "form": form})