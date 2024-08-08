from django.shortcuts import render, redirect, get_object_or_404
from main.forms import (RegistrationForm,
                        CreateAccountForm,
                        NewTransactionForm,
                        UserUpdateForm,
                        AddPaycheckForm,
                        ReceiptUploadForm)
from django.contrib.auth import authenticate, login
from django.contrib.auth.views import PasswordResetView
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from main.models import Account, Transaction, Paychecks
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.contrib.auth import update_session_auth_hash
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import datetime
from django.contrib import messages
from django.core.mail import send_mail
import requests
from bs4 import BeautifulSoup
from .services.azure_service import AzureDocumentIntelligenceService
from .utils.utils import (compress_image,
                          serialize_analysis_results,
                          format_price,
                          clean_and_parse_json_string)
from io import BytesIO
import tempfile
import os
import json
from django.http import HttpResponse



def get_payday_info():
    url = "https://xn--lnningsdag-0cb.dk/"
    response = requests.get(url)
    response.raise_for_status()  # Raise an error for bad status codes

    soup = BeautifulSoup(response.content, 'html.parser')
    payday_span = soup.find('span', id='when')

    if payday_span:
        # only extract the number
        return payday_span.text.split()[1]
    else:
        return "Not available"

def translate_payday_info(weekday):
    weekdays = {
        'mandag': 'Monday',
        'tirsdag': 'Tuesday',
        'onsdag': 'Wednesday',
        'torsdag': 'Thursday',
        'fredag': 'Friday',
        'lørdag': 'Saturday',
        'søndag': 'Sunday'
    }
    return weekdays[weekday]


@login_required
def index(request):
    accounts = Account.objects.filter(user=request.user)
    favorites = Account.objects.filter(user=request.user, isFavorite=True)
    three_recent_transactions = Transaction.objects.filter(account__user=request.user).order_by('-date')[:3]
    current_date = datetime.date.today()
    payday = get_payday_info()
    try:
        payday = int(payday)
    except ValueError:
        pass
    if type(payday) is str:
        payday = translate_payday_info(str(payday))
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
               'current_date': current_date,
               'payday': payday}

    if favorites_count == 0:
        print('No favorites')
        context['accounts'] = accounts
        return render(request, "dashboard.html", context=context)
    elif favorites_count < 3:
        # Fetch additional non-favorite accounts to make up the count to 3
        additional_accounts = Account.objects.filter(user=request.user, isFavorite=False)[:3 - favorites_count]
        combined_accounts = list(favorites) + list(additional_accounts)
        context['accounts'] = combined_accounts
        return render(request, "dashboard.html", context=context)

    else:
        context['accounts'] = favorites
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
        form = CreateAccountForm(request.POST, user=request.user)
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
        form = CreateAccountForm(user=request.user)
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
    if new_value == '':
        messages.error(request, 'New value cannot be empty')
        return redirect('account_info', account_name=account_name)

    valid_fields = ['name', 'account_number', 'account_type', 'accumulated_interest']
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
    account = Account.objects.get(name=account_name, user=request.user)
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
    return render(request, "transactions/new_transaction.html", context={"account": account, "form": form, "accounts": accounts})


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


def transaction_detail(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    return render(request, "transactions/transaction_detail.html", context={"transaction": transaction})


@login_required
@require_POST
def delete_transaction(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, account__user=request.user)
    # Revert back transaction
    account = transaction.account
    if transaction.transaction_type == 'deposit':
        account.balance -= transaction.amount
    elif transaction.transaction_type == 'payment':
        account.balance += transaction.amount
    elif transaction.transaction_type == 'transfer':
        account.balance += transaction.amount

        corresponding_transaction = Transaction.objects.filter(
            account=transaction.transfer_to,
            transaction_type='deposit',
            amount=transaction.amount,
            description=f"Transfer from {account.name}",
            date=transaction.date
        ).first()

        if corresponding_transaction:
            transaction.transfer_to.balance -= corresponding_transaction.amount
            transaction.transfer_to.save()
            corresponding_transaction.delete()

    account.save()
    transaction.delete()
    messages.success(request, 'Transaction deleted and balance reverted.')
    return redirect('account_details', account_name=account.name)


@login_required
def user_info(request):
    user_form = None
    password_form = None

    if request.method == 'POST':
        if 'update_user_info' in request.POST:
            user_form = UserUpdateForm(request.POST, instance=request.user)
            if user_form.is_valid():
                print('User form is valid')
                user_form.save(commit=False)
                if not user_form.cleaned_data['email']:
                    user_form.cleaned_data['email'] = request.user.email
                if not user_form.cleaned_data['username']:
                    user_form.cleaned_data['username'] = request.user.username
                if not user_form.cleaned_data['first_name']:
                    user_form.cleaned_data['first_name'] = request.user.first_name
                if not user_form.cleaned_data['last_name']:
                    user_form.cleaned_data['last_name'] = request.user.last_name
                user_form.save()
                messages.success(request, 'User profile updated successfully.', extra_tags='user_profile')
                return redirect('user_info')
            else:
                print(user_form.errors)
        elif 'change_password' in request.POST:
            print('Changing password')
            password_form = PasswordChangeForm(request.user, request.POST)
            user_form = UserUpdateForm(instance=request.user)  # Initialize the user form in case of errors
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Your Password was successfully updated!', extra_tags='password')
                return redirect('user_info')
            else:
                print(password_form.errors)
    else:
        user_form = UserUpdateForm(instance=request.user)
        password_form = PasswordChangeForm(request.user)

    return render(request, "account/user_account_details.html", context={"user_form": user_form, "password_form": password_form})


@require_POST
@login_required
def delete_user(request):
    user = request.user
    user.delete()
    return redirect('login')


@login_required
def paychecks(request):
    user_paychecks = Paychecks.objects.filter(user=request.user).order_by('-pay_date')
    paginator = Paginator(user_paychecks, 5)  # Show 10 paychecks per page

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {'page_obj': page_obj}
    return render(request, 'paychecks/paychecks.html', context)


@login_required
def add_new_paycheck(request):
    if request.method == "POST":
        form = AddPaycheckForm(request.POST, user=request.user)
        if form.is_valid():
            print(form.errors)
            print(form.cleaned_data)
            # Create a new paycheck
            amount = form.cleaned_data['amount']
            pay_date = form.cleaned_data['pay_date']
            start_pay_period = form.cleaned_data['start_pay_period']
            payout_account = form.cleaned_data['payout_account']
            end_pay_period = form.cleaned_data['end_pay_period']
            employer = form.cleaned_data['employer']
            description = form.cleaned_data['description']
            status = form.cleaned_data['status']

            new_paycheck = Paychecks(
                user=request.user,
                amount=amount,
                pay_date=pay_date,
                pay_period_start=start_pay_period,
                pay_period_end=end_pay_period,
                employer=employer,
                description=description,
                payout_account=payout_account,
                status=status
            )
            new_paycheck.save()
            return redirect('paychecks')
        else:
            print(form.errors)
    else:
        form = AddPaycheckForm(user=request.user)
    return render(request, "paychecks/add_paycheck.html", {"form": form, "accounts": Account.objects.filter(user=request.user)})


@login_required()
def paycheck_info(request, pk):
    paycheck = get_object_or_404(Paychecks, pk=pk)
    return render(request, "paychecks/paycheck_info.html", context={"paycheck": paycheck})


@login_required
@require_POST
def delete_paycheck(request, pk):
    paycheck = get_object_or_404(Paychecks, pk=pk)
    paycheck.delete()
    return redirect('paychecks')


@login_required
@require_POST
def analyze_receipt_view(request, account_name):
    print(request.FILES)
    if request.method == "POST" and 'receipt_image' in request.FILES:
        form = ReceiptUploadForm(request.POST, request.FILES)
        if form.is_valid():
            receipt_image = form.cleaned_data['receipt_image']
            try:

                image_bytes = BytesIO()
                for chunk in receipt_image.chunks():
                    image_bytes.write(chunk)
                image_bytes.seek(0)

                # Compress the image if needed
                compressed_image = compress_image(image_bytes)

                # Save the compressed image to a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                    temp_file.write(compressed_image.getvalue())
                    temp_file_path = temp_file.name

                service = AzureDocumentIntelligenceService()
                analysis_results = service.analyze_receipts(temp_file_path)
                print(analysis_results)
                request.session['analysis_results'] = serialize_analysis_results(analysis_results)
                # Delete the temporary file
                os.remove(temp_file_path)

                return redirect('confirmReceiptAnalysis', account_name=account_name)
            except ValueError as e:
                form.add_error('receipt_image', str(e))
        else:
            return HttpResponse('Invalid form')
    else:
        form = ReceiptUploadForm()
        return HttpResponse('No valid image uploaded')


@login_required
def transaction_import_choice(request, account_name):
    form = ReceiptUploadForm()
    account = get_object_or_404(Account, name=account_name, user=request.user)
    return render(request, 'transactions/transactionImportChoice.html', context={'account': account, 'form': form})


def confirmReceiptAnalysis(request, account_name):
    account = get_object_or_404(Account, name=account_name, user=request.user)
    analysis_results = request.session.get('analysis_results', None)

    if analysis_results in request.session:
        del request.session['analysis_results']

    if isinstance(analysis_results, str):
        try:
            # Deserialize the JSON string back into a Python dictionary
            analysis_results = json.loads(analysis_results)
        except json.JSONDecodeError:
            # Handle JSON decoding errors if any
            analysis_results = None

    analysis_results = analysis_results[0]
    context = {
        "account": account,
        "analysis_results": analysis_results,
        "merchant_name": "N/A",
        "merchant_phone_number": "N/A",
        "merchant_address": "N/A",
        "transaction_date": "N/A",
        "transaction_time": "N/A",
        "Items": [],
        "Subtotal": "N/A",
        "tax": "N/A",
        "tip": "N/A",
        "total": "N/A",
    }
    print(analysis_results)
    fields = analysis_results.get('fields')
    if analysis_results and isinstance(analysis_results, dict) and len(analysis_results) > 0:
        context['merchant_name'] = fields.get('MerchantName', {}).get('valueString', 'N/A')
        context['merchant_phone_number'] = fields.get('MerchantPhoneNumber', {}).get('content', 'N/A')
        if context['merchant_phone_number'] == 'N/A':
            context['merchant_phone_number'] = fields.get('MerchantPhoneNumber', {}).get('valuePhoneNumber', 'N/A')
        context['merchant_address'] = fields.get('MerchantAddress', {}).get('valueString', 'N/A')
        context['transaction_date'] = fields.get('TransactionDate', {}).get('valueDate', 'N/A')
        context['transaction_time'] = fields.get('TransactionTime', {}).get('valueTime', 'N/A')
        items = fields.get('Items', [])
        context['Items'] = [
            {
                'Description': item.get('Description', {}).get('valueString', 'N/A'),
                'Quantity': item.get('Quantity', {}).get('valueNumber', 'N/A'),
                'TotalPrice': format_price(clean_and_parse_json_string(item.get('TotalPrice', {}).get('valueCurrency', 'N/A'))),
            }
            for item in items
        ]

        context['Subtotal'] = format_price(clean_and_parse_json_string(fields.get('Subtotal', {}).get('valueCurrency', {})))
        context['tax'] = format_price(clean_and_parse_json_string(fields.get('TotalTax', {}).get('valueCurrency', {})))
        context['tip'] = format_price(clean_and_parse_json_string(fields.get('Tip', {}).get('valueCurrency', {})))
        context['total'] = format_price(clean_and_parse_json_string(fields.get('Total', {}).get('valueCurrency', {})))
        for key, value in context.items():
            print(f"{key}: {value}")
    return render(request, "transactions/confirmReceiptAnalysis.html", context=context)