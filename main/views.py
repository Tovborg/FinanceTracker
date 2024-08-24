# Import django modules
from django.core.exceptions import MultipleObjectsReturned
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.sessions.models import Session
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views import View
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.http import JsonResponse
from django.contrib.auth import update_session_auth_hash
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.views.generic.edit import FormView
from django.views.generic import TemplateView
# Import app specific modules
from main.forms import (CreateAccountForm,
                        NewTransactionForm,
                        UserUpdateForm,
                        AddPaycheckForm,
                        ReceiptUploadForm,
                        ReceiptAnalysisForm,
                        IncludeTransactionInStatisticsForm)
from main.models import Account, Transaction, Paychecks, Item, UserProfile
# Azure modules
from azure.core.exceptions import HttpResponseError
from .services.azure_service import AzureDocumentIntelligenceService
# Import other modules
from .utils.utils import (compress_image,
                          serialize_analysis_results,
                          create_analysis_context,
                          get_payday_info,
                          handle_transaction,
                          translate_payday_info)
from allauth.mfa.base.views import IndexView as AllauthIndexView
from io import BytesIO
import tempfile
import os


@login_required
def index(request):
    """
    Display the dashboard with the user's accounts, total balance, payday, total expenses, and total income.
    :param request:
    :return:
    """
    accounts = Account.objects.filter(user=request.user)
    favorites = Account.objects.filter(user=request.user, isFavorite=True)

    # Get payday info
    payday = get_payday_info()
    try:
        payday = int(payday)
    except ValueError:
        pass
    if type(payday) is str:
        payday = translate_payday_info(str(payday))

    # Get total expenses and income
    total_expenses = 0
    total_income = 0
    for account in accounts:
        total_expenses += account.get_monthly_expenses()
    for account in accounts:
        total_income += account.get_monthly_income()

    # Get total balance
    total_balance = sum([account.balance for account in accounts])

    # Determine the number of favorites and accounts
    no_favorites = len(favorites)
    no_accounts = len(accounts)

    # Logic to select accounts for display
    if no_favorites >= 3:
        # If there are 3 or more favorites, take the first 3 favorites
        displayed_accounts = favorites[:3]
    else:
        # If there are fewer than 3 favorites, get all favorites and fill with non-favorites
        additional_needed = 3 - no_favorites
        non_favorites = accounts.filter(isFavorite=False)[:additional_needed]
        displayed_accounts = list(favorites) + list(non_favorites)

    # Update the context with the accounts to display and other relevant data
    context = {
        "accounts": displayed_accounts,
        "total_balance": total_balance,
        "no_accounts": no_accounts,
        'total_expenses': total_expenses,
        'total_income': total_income,
        'current_date': timezone.now().date(),
        'current_hour': timezone.now().hour,
        'payday': payday,
    }

    # Render the dashboard with the updated context
    return render(request, "dashboard.html", context=context)


@login_required
def accounts_view(request):
    """
    Display the user's accounts.
    :param request:
    :return:
    """
    user_accounts = Account.objects.filter(user=request.user)
    return render(request, "bank_accounts/account.html", context={"accounts": user_accounts})


@login_required
def account_info(request, account_name):
    """
    Display information about a specific account.
    :param request:
    :param account_name:
    :return:
    """
    account = get_object_or_404(Account, name=account_name, user=request.user)
    return render(request, "bank_accounts/account_info.html", context={"account": account})


@require_POST  # Only allow POST requests
@login_required
def delete_account(request, account_name):
    """
    Delete an account and all transactions associated with it.
    :param request:
    :param account_name:
    :return:
    """
    account = get_object_or_404(Account, name=account_name, user=request.user)
    # Delete transactions associated with the account
    account.transaction_set.all().delete()
    account.delete()
    return redirect('account')


@login_required
def account_view(request, account_name):
    """
    Display the details and transactions for a specific account. Paginate the transactions with 5 transactions per page.
    :param request:
    :param account_name:
    :return:
    """
    # Handle exceptional cases where multiple accounts with the same name exist.
    # User should not have multiple accounts with the same name
    try:
        account = get_object_or_404(Account, name=account_name, user=request.user)
    except MultipleObjectsReturned:
        account = Account.objects.filter(name=account_name, user=request.user).first()
    transactions_list = account.transaction_set.all().order_by('-date')  # Get all transactions for the account and order by date

    # Paginate the transactions with 5 transactions per page
    paginator = Paginator(transactions_list, 5)
    # Get the page number from the request
    page_number = request.GET.get('page')
    # Get the transactions for the current page
    try:
        transactions = paginator.page(page_number)
    except PageNotAnInteger:
        transactions = paginator.page(1)
    except EmptyPage:
        transactions = paginator.page(paginator.num_pages)

    return render(request, "bank_accounts/account_details.html", context={"account": account, "transactions": transactions})


class AddAccountView(LoginRequiredMixin, View):
    template_name = "bank_accounts/add_account.html"

    def get(self, request, *args, **kwargs):
        form = CreateAccountForm(user=request.user)
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        form = CreateAccountForm(request.POST, user=request.user)
        if form.is_valid():
            # Create a new account
            new_account = Account(
                user=request.user,
                name=form.cleaned_data['account_name'],
                balance=form.cleaned_data['account_balance'],
                account_type=form.cleaned_data['account_type'],
                description=form.cleaned_data['description'],
                account_number=form.cleaned_data['account_number']
            )
            new_account.save()
            return redirect('account')
        else:
            print(form.errors)

        return render(request, self.template_name, {"form": form})


@login_required
@require_POST
def edit_account(request, account_name, field):
    """
    Edit an account's field. The request comes from the account_info page.
    :param request:
    :param account_name:
    :param field:
    :return:
    """
    account = get_object_or_404(Account, name=account_name, user=request.user)

    new_value = request.POST.get('new_value')  # Get the new value from the POST request

    # Check if the new value is empty
    if not new_value:
        messages.error(request, 'New value cannot be empty')
        return redirect('account_info', account_name=account_name)

    # Check if the field is valid
    valid_fields = ['name', 'account_number', 'account_type', 'accumulated_interest']
    if field in valid_fields:
        # Check if the new name already exists for another account
        if field == 'name' and Account.objects.filter(name=new_value, user=request.user).exclude(
                pk=account.pk).exists():
            messages.error(request, 'An account with this name already exists.')
            return redirect('account_info', account_name=account_name)
        # Update the field and save the account
        setattr(account, field, new_value)
        account.save()
        # Display a success message
        messages.success(request, f'{field.replace("_", " ").capitalize()} updated successfully.')
    else:
        # Display an error message for invalid fields
        messages.error(request, 'Invalid field.')

    # Update account_name for the redirect in case the name was changed
    if field == 'name':
        account_name = account.name

    return redirect('account_info', account_name=account_name)


@require_POST
@login_required
def update_favorite(request):
    """
    Update the favorite status of an account, the request comes from JavaScript to make the request experience smoother.
    That's also the reason why the response is a JSON response and the view is csrf_exempt.
    :param request:
    :return:
    """
    account_name = request.POST.get('account_name')  # Get the account name from the POST request
    account = Account.objects.get(name=account_name, user=request.user)  # Get the account
    account.isFavorite = not account.isFavorite  # Toggle the favorite status
    account.save()  # Save the account
    return JsonResponse({'status': 'ok'})  # Return a JSON response


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

            handle_transaction(transaction_type, amount, account, transaction, transfer_to)
            return redirect('account_details', account_name=account_name)
        else:
            print(form.errors)
    else:
        form = NewTransactionForm(user=request.user)
    return render(request, "transactions/new_transaction.html", context={"account": account, "form": form, "accounts": accounts})


class TransactionDetailView(View, LoginRequiredMixin):
    """
    Display the details of a transaction. And handle the form to include the transaction in statistics.
    """
    template_name = "transactions/transaction_detail.html"

    def get(self, request, pk):
        transaction = get_object_or_404(Transaction, pk=pk)  # Get the transaction
        if transaction.transaction_type == 'purchase':
            items = transaction.item_set.all()
            return render(request, "transactions/transaction_detail.html",
                          context={"transaction": transaction, "items": items})
        return render(request, self.template_name, context={"transaction": transaction})

    def post(self, request, pk):
        transaction = get_object_or_404(Transaction, pk=pk)  # Get the transaction
        form = IncludeTransactionInStatisticsForm(request.POST)  # Get the form
        if form.is_valid():
            include_in_statistics = form.cleaned_data['include_in_statistics']  # Get the value of the form
            transaction.include_in_statistics = include_in_statistics  # Update the transaction
            transaction.save()  # Save the transaction
            return redirect('transaction_detail', pk=pk)  # Redirect to the transaction detail page
        else:
            return redirect('transaction_detail', pk=pk)  # Redirect to the transaction detail page


@login_required
@require_POST
def delete_transaction(request, pk):
    """
    Delete a transaction and revert the balance of the account.
    :param request:
    :param pk:
    :return:
    """
    transaction = get_object_or_404(Transaction, pk=pk, account__user=request.user)  # Get the transaction

    # Revert back transaction
    account = transaction.account
    # Match transaction type and revert back the balance
    match transaction.transaction_type:
        case 'deposit':
            account.balance -= transaction.amount
        case 'payment':
            account.balance += transaction.amount
        case 'wage deposit':
            account.balance -= transaction.amount
        case 'transfer':
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
        case 'purchase':
            account.balance += transaction.amount
        case _:
            pass

    account.save()  # Save the account
    transaction.delete()  # Delete the transaction
    return redirect('account_details', account_name=account.name)


class UserInfoView(LoginRequiredMixin, View):
    """
    Display the user's account details and handle the form to update the user's information and change password.
    As well as delete the user's account.
    """
    template_name = "account/user_account_details.html"
    user_form_class = UserUpdateForm
    password_form_class = PasswordChangeForm

    def get(self, request, *args, **kwargs):
        user_form = self.user_form_class(instance=request.user)
        password_form = self.password_form_class(request.user)
        return self.render_forms(request, user_form, password_form)

    def post(self, request, *args, **kwargs):
        if 'update_user_info' in request.POST:
            return self.handle_user_info_update(request)
        elif 'change_password' in request.POST:
            return self.handle_password_change(request)
        else:
            return self.get(request)

    def handle_user_info_update(self, request):
        user_form = self.user_form_class(request.POST, instance=request.user)
        password_form = self.password_form_class(request.user)  # Pre-fill password form

        if user_form.is_valid():
            self.update_user_info(user_form, request)
            messages.success(request, 'User profile updated successfully.', extra_tags='user_profile')
            return redirect('user_info')
        else:
            return self.render_forms(request, user_form, password_form)

    def update_user_info(self, user_form, request):
        user = user_form.save(commit=False)
        user.email = user_form.cleaned_data['email'] or request.user.email
        user.username = user_form.cleaned_data['username'] or request.user.username
        user.first_name = user_form.cleaned_data['first_name'] or request.user.first_name
        user.last_name = user_form.cleaned_data['last_name'] or request.user.last_name
        user.save()

    def handle_password_change(self, request):
        password_form = self.password_form_class(request.user, request.POST)
        user_form = self.user_form_class(instance=request.user)  # Pre-fill user form

        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)  # Important to prevent logout after password change
            messages.success(request, 'Your password was successfully updated!', extra_tags='password')
            return redirect('user_info')
        else:
            return self.render_forms(request, user_form, password_form)

    def render_forms(self, request, user_form, password_form):
        return render(request, self.template_name, context={
            "user_form": user_form,
            "password_form": password_form
        })


@require_POST
@login_required
def delete_user(request):
    """
    Delete the user's account and log the user out.
    :param request:
    :return:
    """
    user = request.user
    user.delete()
    return redirect('account_login')


@login_required
def paychecks(request):
    """
    Display the user's paychecks with pagination
    :param request:
    :return:
    """
    user_paychecks = Paychecks.objects.filter(user=request.user).order_by('-pay_date')  # Get paychecks
    paginator = Paginator(user_paychecks, 5)  # Show 10 paychecks per page

    page_number = request.GET.get('page')  # Get the page number from the request
    page_obj = paginator.get_page(page_number)  # Get the paychecks for the current page
    context = {'page_obj': page_obj}  # Update the context with the paychecks for the current page
    return render(request, 'paychecks/paychecks.html', context)


class AddNewPaycheckView(LoginRequiredMixin, FormView):
    """
    Display the form to add a new paycheck and handle the form submission.
    """
    form_class = AddPaycheckForm
    template_name = "paychecks/add_paycheck.html"
    success_url = reverse_lazy('paychecks')

    def get_form_kwargs(self):
        """Passes the user to the form."""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        """If the form is valid, save the associated model."""
        amount = form.cleaned_data['amount']
        pay_date = form.cleaned_data['pay_date']
        start_pay_period = form.cleaned_data['start_pay_period']
        payout_account = form.cleaned_data['payout_account']
        end_pay_period = form.cleaned_data['end_pay_period']
        employer = form.cleaned_data['employer']
        description = form.cleaned_data['description']
        status = form.cleaned_data['status']

        new_paycheck = Paychecks(
            user=self.request.user,
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
            self.create_wage_deposit(new_paycheck)

        return super().form_valid(form)

    def create_wage_deposit(self, paycheck):
        """Create a wage deposit transaction."""
        payout_account = paycheck.payout_account
        wage_deposit = Transaction(
            account=payout_account,
            transaction_type='wage deposit',
            amount=paycheck.amount,
            date=paycheck.pay_date,
            description=f"Wage deposit from {paycheck.employer}",
            balance_after=payout_account.balance + paycheck.amount
        )
        wage_deposit.save()
        handle_transaction('wage deposit', paycheck.amount, payout_account, wage_deposit)

    def get_context_data(self, **kwargs):
        """Add accounts to the context."""
        context = super().get_context_data(**kwargs)
        context['accounts'] = Account.objects.filter(user=self.request.user)
        return context


@login_required()
def paycheck_info(request, pk):
    """
    Display the details of a paycheck.
    :param request:
    :param pk:
    :return:
    """
    paycheck = get_object_or_404(Paychecks, pk=pk)
    return render(request, "paychecks/paycheck_info.html", context={"paycheck": paycheck})


@login_required
@require_POST
def delete_paycheck(request, pk):
    """
    View to delete a paycheck and revert the transaction if the paycheck was paid.
    :param request:
    :param pk:
    :return:
    """
    paycheck = get_object_or_404(Paychecks, pk=pk)  # Get the paycheck
    # Revert transaction if paycheck was paid
    if paycheck.status == 'paid':
        # revert transaction
        wage_deposit = Transaction.objects.filter(
            account=paycheck.payout_account,
            transaction_type='wage deposit',
            amount=paycheck.amount,
            date=paycheck.pay_date,
            description=f"Wage deposit from {paycheck.employer}"
        ).first()  # Get the wage deposit transaction
        if wage_deposit:
            # Revert the transaction from the payout account
            paycheck.payout_account.balance -= wage_deposit.amount
            paycheck.payout_account.save()
            wage_deposit.delete()
    paycheck.delete()
    return redirect('paychecks')


class AnalyzeReceiptView(LoginRequiredMixin, View):
    """
    Here the post request is handled, image compressed, and sent to the Azure service for analysis. Doesn't return
    any response, but redirects to the confirmReceiptAnalysis view while storing the analysis results in the session.
    """
    def post(self, request, account_name):
        if 'receipt_image' in request.FILES:
            form = ReceiptUploadForm(request.POST, request.FILES)
            if form.is_valid():
                receipt_image = form.cleaned_data['receipt_image']
                try:
                    image_bytes = self.get_image_bytes(receipt_image)

                    compressed_image = compress_image(image_bytes)

                    temp_file_path = self.save_temp_image(compressed_image)

                    service = AzureDocumentIntelligenceService()

                    try:
                        analysis_results = service.analyze_receipts(temp_file_path)
                        request.session['analysis_results'] = serialize_analysis_results(analysis_results)
                    except HttpResponseError as e:
                        request.session['error_message'] = str(e)
                        del request.session['analysis_results']
                    finally:
                        os.remove(temp_file_path)

                    return redirect('confirmReceiptAnalysis', account_name=account_name)
                except ValueError as e:
                    form.add_error('receipt_image', str(e))
            else:
                return HttpResponse('Invalid form')
        else:
            return HttpResponse('No valid image uploaded')

    @staticmethod
    def get_image_bytes(receipt_image: InMemoryUploadedFile) -> BytesIO:
        """Reads the uploaded image into a BytesIO object."""
        image_bytes = BytesIO()
        for chunk in receipt_image.chunks():
            image_bytes.write(chunk)
        image_bytes.seek(0)
        return image_bytes

    @staticmethod
    def save_temp_image(compressed_image: BytesIO) -> str:
        """Saves the compressed image to a temporary file and returns the file path."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            temp_file.write(compressed_image.getvalue())
            return temp_file.name


class TransactionImportChoiceView(LoginRequiredMixin, TemplateView):
    """
    Display the choice between manual transaction creation and receipt analysis
    """
    template_name = 'transactions/transactionImportChoice.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        account_name = kwargs.get('account_name')
        account = get_object_or_404(Account, name=account_name, user=self.request.user)

        form = ReceiptUploadForm()
        error_message = self.request.session.pop('error_message', None)

        context.update({
            'account': account,
            'form': form,
            'error_message': error_message,
        })
        return context


class ConfirmReceiptAnalysisView(LoginRequiredMixin, View):
    """
    Display the analysis results and form to confirm the analysis and edit possible missing fields or errors.
    Create the transaction and items if the form is valid and the user confirms the analysis.
    """
    template_name = "transactions/confirmReceiptAnalysis.html"

    def get(self, request, account_name):
        account = self._get_account(request, account_name)
        form = ReceiptAnalysisForm()
        context = self._create_context(request, account, form)
        return render(request, self.template_name, context)

    def post(self, request, account_name):
        account = get_object_or_404(Account, name=account_name, user=request.user)
        form = ReceiptAnalysisForm(request.POST)

        if form.is_valid():
            if self._process_items(request, form):
                cleaned_data = form.cleaned_data
                new_transaction = self._create_transaction(account, cleaned_data)
                self._create_items(request, new_transaction)
                account.balance -= cleaned_data['total']
                account.save()
                return redirect('account_details', account_name=account_name)
            else:
                context = self._create_context(request, account, form)
                return render(request, self.template_name, context)
        else:
            context = self._create_context(request, account, form)
            return render(request, self.template_name, context)

    def _create_context(self, request, account, form):
        """
        Create the context for the view using the create_analysis_context utility function
        """
        return create_analysis_context(request, account, form, request.session.get('analysis_results'))

    def _process_items(self, request, form):
        """
        Process the items in the form and check if all fields are filled.
        """
        item_count = len([key for key in request.POST if key.startswith('description_')])

        for i in range(1, item_count + 1):
            description = request.POST.get(f'description_{i}')
            quantity = request.POST.get(f'quantity_{i}')
            price = request.POST.get(f'price_{i}')

            if not all([description, quantity, price]):
                form.add_error(None, f"Item {i} has missing fields. All fields are required.")
                return False

        return True

    def _create_transaction(self, account, cleaned_data):
        new_transaction = Transaction(
            account=account,
            transaction_type='purchase',
            amount=cleaned_data['total'],
            date=cleaned_data['transaction_date'],
            balance_after=account.balance - cleaned_data['total'],
            merchant_name=cleaned_data['merchant_name'],
            merchant_address=cleaned_data.get('merchant_address', 'N/A') if cleaned_data.get('merchant_address') != 'N/A' else None,
            merchant_phone_number=cleaned_data.get('merchant_phone_number', 'N/A') if cleaned_data.get('merchant_phone_number') != 'N/A' else None,
            tax=cleaned_data.get('tax', 0.0) if cleaned_data.get('tax') != 0.0 else None,
        )
        new_transaction.save()
        return new_transaction

    def _create_items(self, request, transaction):
        item_count = len([key for key in request.POST if key.startswith('description_')])

        for i in range(1, item_count + 1):
            Item.objects.create(
                transaction=transaction,
                description=request.POST.get(f'description_{i}'),
                price=request.POST.get(f'price_{i}'),
                quantity=request.POST.get(f'quantity_{i}')
            )


class CustomSecurityIndexView(AllauthIndexView):
    """
    Custom view for the allauth mfa index view, so we can add additional context data. such as user sessions.
    """
    template_name = "mfa/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_sessions = self._get_user_sessions()
        context['user_sessions'] = user_sessions
        return context

    def _get_user_sessions(self):
        sessions = Session.objects.filter(expire_date__gte=timezone.now())
        user_id = str(self.request.user.id)
        current_session_key = self.request.session.session_key

        user_sessions = [
            self._extract_session_info(session, session.get_decoded(), current_session_key)
            for session in sessions
            if session.get_decoded().get('_auth_user_id') == user_id
        ]

        return user_sessions

    def _extract_session_info(self, session, session_data, current_session_key):
        session_info = session_data.get('session_info', {})

        return {
            'session_key': session.session_key,
            'expire_date': session.expire_date,
            'ip_address': session_info.get('ip_address'),
            'device': session_info.get('device'),
            'browser': session_info.get('browser'),
            'os': session_info.get('os'),
            'login_time': session_info.get('login_time'),
            'country': session_info.get('country'),
            'city': session_info.get('city'),
            'latitude': session_info.get('latitude'),
            'longitude': session_info.get('longitude'),
            'is_current_session': session.session_key == current_session_key
        }


class TerminateAllSessionsView(LoginRequiredMixin, View):
    """
    View to terminate all active sessions for the user.
    """
    def post(self, request, *args, **kwargs):
        sessions = Session.objects.filter(expire_date__gte=timezone.now())

        if not sessions.exists():
            messages.error(request, 'No active sessions to terminate.')
            return redirect('mfa_index')

        user_id = str(request.user.id)
        terminated = False

        for session in sessions:
            data = session.get_decoded()
            if data.get('_auth_user_id') == user_id:
                session.delete()
                terminated = True

        if terminated:
            messages.success(request, 'All active sessions terminated.')
        else:
            messages.error(request, 'No active sessions to terminate.')

        return redirect('mfa_index')


@require_POST
@login_required
def terminate_session(request, session_key):
    """
    View to terminate a specific session.
    :param request:
    :param session_key:
    :return:
    """
    session = Session.objects.get(session_key=session_key)
    session.delete()
    messages.success(request, f'Session with session key {session_key} terminated.')
    return redirect('mfa_index')
