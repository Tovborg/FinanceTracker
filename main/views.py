from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
# Use @login_required decorator to ensure only authenticated users can access the view

def index(request):
    return render(request, "dashboard.html")

