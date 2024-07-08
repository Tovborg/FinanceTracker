#main/urls.py

from django.urls import include, path
from main.views import index

urlpatterns = [
    path("", index, name="index"),
]