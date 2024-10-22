from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from allauth.account.forms import SignupForm
from main.models import Account, Paychecks
from django.core.exceptions import ValidationError
from django.core.validators import validate_email, FileExtensionValidator
import datetime


class CustomSignupForm(SignupForm):
    first_name = forms.CharField(max_length=30, required=True, label='First Name')
    last_name = forms.CharField(max_length=30, required=True, label='Last Name')

    def save(self, request):
        user = super(CustomSignupForm, self).save(request)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()
        return user


class CreateAccountForm(forms.Form):
    ACCOUNT_TYPES = (
        ('savings', 'Savings'),
        ('checking', 'Checking'),
        ('vacation', 'Vacation'),
        ('retirement', 'Retirement'),
        ('other', 'Other'),
        ('credit card', 'Credit Card'),
    )
    CREDITCARD_TYPES = (
        ('visa', 'Visa'),
        ('mastercard', 'Mastercard'),
        ('dankort', 'Dankort'),
        ('american express', 'American Express'),
        ('discover', 'Discover'),
        ('other', 'Other')
    )
    account_name = forms.CharField(max_length=20)
    account_balance = forms.DecimalField(max_digits=10, decimal_places=2, required=True)
    creditcard_type = forms.ChoiceField(choices=CREDITCARD_TYPES, required=False)
    account_type = forms.ChoiceField(choices=ACCOUNT_TYPES)
    account_number = forms.CharField(max_length=50, required=False)
    # field for uploading a file
    description = forms.CharField(widget=forms.Textarea, required=False)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)

    def clean_account_name(self):
        account_name = self.cleaned_data.get('account_name')
        # Check if user already has an account with that name
        if Account.objects.filter(name=account_name, user=self.user).exists():
            raise ValidationError("An account with that name already exists.")
        if len(account_name) > 20:
            raise ValidationError("Account name must be 20 characters or less.")
        return account_name



class NewTransactionForm(forms.Form):
    TRANSACTION_TYPES = (
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('payment', 'Payment'),
        ('transfer', 'Transfer')
    )
    transaction_type = forms.ChoiceField(choices=TRANSACTION_TYPES, required=True)
    amount = forms.DecimalField(max_digits=10, decimal_places=2, required=True)
    date = forms.DateField(widget=forms.SelectDateWidget, required=True)
    description = forms.CharField(widget=forms.Textarea, required=False)
    transfer_to = forms.ModelChoiceField(queryset=Account.objects.none(), required=False)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super(NewTransactionForm, self).__init__(*args, **kwargs)
        if user:
            self.fields['transfer_to'].queryset = Account.objects.filter(user=user)

    def clean(self):
        cleaned_data = super().clean()
        transaction_type = cleaned_data.get('transaction_type')
        transfer_to = cleaned_data.get('transfer_to')
        if transaction_type == 'transfer' and not transfer_to:
            self.add_error('transfer_to', 'This field is required when transaction type is Transfer')
        return cleaned_data


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'username']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].required = False
        self.fields['email'].required = False
        self.fields['first_name'].required = False
        self.fields['last_name'].required = False

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            try:
                validate_email(email)
            except ValidationError:
                raise ValidationError("Enter a valid email address.")
        if email and User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError("This email is already associated with an account.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username and User.objects.filter(username=username).exists():
            raise ValidationError("This username is already taken.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('first_name'):
            cleaned_data['first_name'] = self.instance.first_name
        if not cleaned_data.get('last_name'):
            cleaned_data['last_name'] = self.instance.last_name
        if not cleaned_data.get('email'):
            cleaned_data['email'] = self.instance.email
        if not cleaned_data.get('username'):
            cleaned_data['username'] = self.instance.username
        return cleaned_data


class AddPaycheckForm(forms.Form):
    PAYCHECK_STATUS = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
    )
    amount = forms.DecimalField(max_digits=10, decimal_places=2, required=True)
    payout_account = forms.ModelChoiceField(queryset=Account.objects.none(), required=True)
    pay_date = forms.DateField(widget=forms.SelectDateWidget, required=True)
    start_pay_period = forms.DateField(widget=forms.SelectDateWidget, required=True)
    end_pay_period = forms.DateField(widget=forms.SelectDateWidget, required=True)
    employer = forms.CharField(max_length=50, required=True)
    description = forms.CharField(widget=forms.Textarea, required=False)
    status = forms.ChoiceField(choices=PAYCHECK_STATUS, required=True)

    class Meta:
        model = Paychecks
        fields = ['amount', 'payout_account', 'pay_date', 'start_pay_period', 'end_pay_period', 'employer', 'description', 'status']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['payout_account'].queryset = Account.objects.filter(user=user)

    def clean(self):
        cleaned_data = super().clean()
        start_pay_period = cleaned_data.get('start_pay_period')
        end_pay_period = cleaned_data.get('end_pay_period')
        status = cleaned_data.get('status')

        payout_date = cleaned_data.get('pay_date')

        if start_pay_period and end_pay_period and start_pay_period > end_pay_period:
            raise ValidationError("End of pay period must be after start of pay period.")

        if status == 'pending' and payout_date <= datetime.date.today():
            raise ValidationError("Pay date must be in the future for pending paychecks.")

        if payout_date == 'paid' and payout_date > datetime.date.today():
            raise ValidationError("Pay date must be in the past for paid paychecks.")

        if payout_date < end_pay_period:
            raise ValidationError("Pay date must be after the end of the pay period.")


        return cleaned_data


class ReceiptUploadForm(forms.Form):
    receipt_image = forms.ImageField(required=True,
                                     validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])])


class ReceiptAnalysisForm(forms.Form):
    merchant_name = forms.CharField(max_length=50, required=True)
    merchant_phone_number = forms.CharField(max_length=15, required=False)
    merchant_address = forms.CharField(max_length=255, required=False)
    transaction_date = forms.DateField(widget=forms.SelectDateWidget, required=True)
    transaction_time = forms.TimeField(required=True)
    subtotal = forms.DecimalField(max_digits=10, decimal_places=2, required=False)
    tax = forms.DecimalField(max_digits=10, decimal_places=2, required=False)
    total = forms.DecimalField(max_digits=10, decimal_places=2, required=True)

    def clean_total(self):
        total = self.cleaned_data.get('total')
        print(total)
        if total <= 0 or total == 0.0:
            raise ValidationError("Total must be greater than 0.")
        return total


class IncludeTransactionInStatisticsForm(forms.Form):
    include_in_statistics = forms.BooleanField(required=False)
