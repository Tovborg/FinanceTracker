from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class RegistrationForm(UserCreationForm):
    Email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'Email', 'password1', 'password2']