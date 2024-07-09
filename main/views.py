from django.shortcuts import render, redirect
from main.forms import RegistrationForm
from django.contrib.auth import authenticate, login
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
