from django.shortcuts import render, redirect, get_object_or_404
from main.forms import (CreateAccountForm,
                        NewTransactionForm,
                        UserUpdateForm,
                        AddPaycheckForm,
                        ReceiptUploadForm,
                        ReceiptAnalysisForm,
                        IncludeTransactionInStatisticsForm)
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib.sessions.models import Session
from main.models import Account, Transaction, Paychecks, Item
from django.views.decorators.http import require_POST
from django.views import View
from django.http import JsonResponse
from django.contrib.auth import update_session_auth_hash
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import datetime
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from azure.core.exceptions import HttpResponseError
from .services.azure_service import AzureDocumentIntelligenceService
from .utils.utils import (compress_image,
                          serialize_analysis_results,
                          create_analysis_context,
                          get_payday_info,
                          handleTransaction)
from allauth.mfa.base.views import IndexView as AllauthIndexView
from io import BytesIO
import tempfile
import os
import json
from django.http import HttpResponse


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
               'current_date': timezone.now().date(),
               'current_hour': timezone.now().hour,
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


# Views to display and handle accounts
@login_required
def account_view(request):
    user_accounts = Account.objects.filter(user=request.user)
    return render(request, "bank_accounts/account.html", context={"accounts": user_accounts})


@login_required
def account_info(request, account_name):
    account = get_object_or_404(Account, name=account_name, user=request.user)
    return render(request, "bank_accounts/account_info.html", context={"account": account})


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

    return render(request, "bank_accounts/account_details.html", context={"account": account, "transactions": transactions})


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
            print(f"Transfer to: {transfer_to.balance}")
            # Calculate balance after transaction
            if transaction_type == 'deposit':
                balance_after = account.balance + amount
            elif transaction_type == 'withdrawal':
                balance_after = account.balance - amount
            elif transaction_type == 'payment':
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

            handleTransaction(transaction_type, amount, account, transaction, transfer_to)
            return redirect('account_details', account_name=account_name)
        else:
            print(form.errors)
    else:
        form = NewTransactionForm(user=request.user)
    return render(request, "transactions/new_transaction.html", context={"account": account, "form": form, "accounts": accounts})


class TransactionDetailView(View, LoginRequiredMixin):
    def get(self, request, pk):
        transaction = get_object_or_404(Transaction, pk=pk)
        if transaction.transaction_type == 'purchase':
            items = transaction.item_set.all()
            return render(request, "transactions/transaction_detail.html",
                          context={"transaction": transaction, "items": items})
        return render(request, "transactions/transaction_detail.html", context={"transaction": transaction})

    def post(self, request, pk):
        transaction = get_object_or_404(Transaction, pk=pk)
        form = IncludeTransactionInStatisticsForm(request.POST)
        if form.is_valid():
            include_in_statistics = form.cleaned_data['include_in_statistics']
            transaction.include_in_statistics = include_in_statistics
            transaction.save()
            return redirect('transaction_detail', pk=pk)
        else:
            print(form.errors)
            return redirect('transaction_detail', pk=pk)







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
    elif transaction.transaction_type == 'wage deposit':
        account.balance -= transaction.amount
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

    elif transaction.transaction_type == 'purchase':
        account.balance += transaction.amount


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
            if new_paycheck.status == 'paid':
                new_wage_deposit = Transaction(
                    account=payout_account,
                    transaction_type='wage deposit',
                    amount=amount,
                    date=pay_date,
                    description=f"Wage deposit from {employer}",
                    balance_after=payout_account.balance + amount
                )
                new_wage_deposit.save()
                handleTransaction('wage deposit', amount, payout_account, new_wage_deposit)
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
    if paycheck.status == 'paid':
        # revert transaction
        wage_deposit = Transaction.objects.filter(
            account=paycheck.payout_account,
            transaction_type='wage deposit',
            amount=paycheck.amount,
            date=paycheck.pay_date,
            description=f"Wage deposit from {paycheck.employer}"
        ).first()
        if wage_deposit:
            paycheck.payout_account.balance -= wage_deposit.amount
            paycheck.payout_account.save()
            wage_deposit.delete()
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
                try:
                    analysis_results = service.analyze_receipts(temp_file_path)
                    request.session['analysis_results'] = serialize_analysis_results(analysis_results)
                    os.remove(temp_file_path)
                except HttpResponseError as e:
                    request.session['error_message'] = str(e)
                    os.remove(temp_file_path)
                    del request.session['analysis_results']
                    return redirect('new_transaction_choice', account_name=account_name)

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
    try:
        error_message = request.session.get('error_message')
        del request.session['error_message']
    except KeyError:
        error_message = None
    return render(request, 'transactions/transactionImportChoice.html', context={'account': account,
                                                                                 'form': form,
                                                                                 'error_message': error_message})


class ConfirmReceiptAnalysisView(View, LoginRequiredMixin):
    def get(self, request, account_name):
        account = get_object_or_404(Account, name=account_name, user=request.user)
        form = ReceiptAnalysisForm()
        # Clear session data
        context = create_analysis_context(request, account, form, request.session.get('analysis_results'))
        return render(request, "transactions/confirmReceiptAnalysis.html", context=context)

    def post(self, request, account_name):
        account = get_object_or_404(Account, name=account_name, user=request.user)
        form = ReceiptAnalysisForm(request.POST)

        if form.is_valid():
            # Extract form data (if needed)
            # Cleaned data is accessed via form.cleaned_data
            print(form.cleaned_data.get('total'))
            cleaned_data = {
                'merchant_name': form.cleaned_data.get('merchant_name'),
                'merchant_phone_number': form.cleaned_data.get('merchant_phone_number'),
                'merchant_address': form.cleaned_data.get('merchant_address'),
                'transaction_date': form.cleaned_data.get('transaction_date'),
                'transaction_time': form.cleaned_data.get('transaction_time'),
                'subtotal': form.cleaned_data.get('subtotal'),
                'tax': form.cleaned_data.get('tax'),
                'total': form.cleaned_data.get('total'),
            }

            # Process items
            item_count = len([key for key in request.POST if key.startswith('description_')])
            has_error = False

            items = [{
                'Description': request.POST.get(f'description_{i}'),
                'Quantity': request.POST.get(f'quantity_{i}'),
                'TotalPrice': request.POST.get(f'price_{i}')
            } for i in range(1, item_count + 1)]

            for i in range(1, item_count + 1):
                description = request.POST.get(f'description_{i}')
                quantity = request.POST.get(f'quantity_{i}')
                price = request.POST.get(f'price_{i}')

                if not description or not quantity or not price:
                    form.add_error(None, f"Item {i} has missing fields. All fields are required.")
                    has_error = True
                    break  # Optionally, break the loop if you only want the first error

            if has_error:
                # Return form with errors
                return render(request, "transactions/confirmReceiptAnalysis.html",
                              context=create_analysis_context(request, account, form,
                                                              request.session.get('analysis_results')))

            new_transaction = Transaction(
                account=account,
                transaction_type='purchase',
                amount=cleaned_data['total'],
                date=cleaned_data['transaction_date'],
                balance_after=account.balance - cleaned_data['total'],
                merchant_name=cleaned_data['merchant_name'],
            )
            if cleaned_data['merchant_address'] != 'N/A':
                new_transaction.merchant_address = cleaned_data['merchant_address']
            if cleaned_data['merchant_phone_number'] != 'N/A':  # Check if phone number is available
                new_transaction.merchant_phone_number = cleaned_data['merchant_phone_number']
            if cleaned_data['tax'] != 0.0:
                new_transaction.tax = cleaned_data['tax']
            new_transaction.save()

            # Update account balance
            account.balance -= cleaned_data['total']
            account.save()

            for item in items:
                new_item = Item(
                    transaction=new_transaction,
                    description=item['Description'],
                    price=item['TotalPrice'],
                    quantity=item['Quantity']
                )
                new_item.save()


            # Create context and redirect
            context = create_analysis_context(request, account, form, request.session.get('analysis_results'))
            return redirect('account_details', account_name=account_name)

        else:
            # Handle form errors
            print(form.errors)  # Use logging in production
            context = create_analysis_context(request, account, form, request.session.get('analysis_results'))
            return render(request, "transactions/confirmReceiptAnalysis.html", context=context)


class CustomSecurityIndexView(AllauthIndexView):
    template_name = "mfa/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        sessions = Session.objects.filter(expire_date__gte=timezone.now())

        user_sessions = []
        for session in sessions:
            data = session.get_decoded()
            # print(data)
            if data.get('_auth_user_id') == str(self.request.user.id):
                session_info = data.get('session_info')
                print(session_info)
                if isinstance(session_info, dict):
                    user_sessions.append({
                        'session_key': session.session_key,
                        'expire_date': session.expire_date,
                        'ip_address': session_info.get('ip_address'),
                        'device': session_info.get('device'),
                        'browser': session_info.get('browser'),
                        'os': session_info.get('os'),
                        'login_time': session_info.get('login_time'),
                    })
                else:
                    user_sessions.append({
                        'session_key': session.session_key,
                        'expire_date': session.expire_date,
                        'ip_address': None,
                        'device': None,
                        'browser': None,
                        'os': None,
                        'login_time': None,
                    })
        context['user_sessions'] = user_sessions
        return context
