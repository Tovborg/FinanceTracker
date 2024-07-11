from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class RegistrationForm(UserCreationForm):
    Email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'Email', 'password1', 'password2']

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