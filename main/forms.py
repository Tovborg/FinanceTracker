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
        ('Other', 'Other')
    )
    account_name = forms.CharField(max_length=50)
    account_balance = forms.DecimalField(max_digits=10, decimal_places=2, required=True)
    account_type = forms.ChoiceField(choices=ACCOUNT_TYPES)
    # field for uploading a file
    description = forms.CharField(widget=forms.Textarea, required=False)