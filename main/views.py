from django.shortcuts import render, redirect
from main.forms import RegistrationForm, CreateAccountForm
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from main.models import Account
# Use @login_required decorator to ensure only authenticated users can access the view


def index(request):
    return render(request, "dashboard.html")


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


# Views to display and handler accounts
@login_required
def account_view(request):
    user_accounts = Account.objects.filter(user=request.user)
    print(user_accounts)
    print(len(user_accounts))
    return render(request, "account/account.html", context={"accounts": user_accounts})


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