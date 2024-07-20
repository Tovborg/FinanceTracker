from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from main.models import Account
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=50, required=True)
    last_name = forms.CharField(max_length=50, required=True)
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'password1', 'password2']

class CreateAccountForm(forms.Form):
    ACCOUNT_TYPES = (
        ('savings', 'Savings'),
        ('checking', 'Checking'),
        ('Vacation', 'Vacation'),
        ('Retirement', 'Retirement'),
        ('other', 'Other')
    )
    account_name = forms.CharField(max_length=50)
    account_balance = forms.DecimalField(max_digits=10, decimal_places=2, required=True)
    account_type = forms.ChoiceField(choices=ACCOUNT_TYPES)
    account_number = forms.CharField(max_length=50, required=False)
    # field for uploading a file
    description = forms.CharField(widget=forms.Textarea, required=False)

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
