#main/urls.py

from django.urls import include, path
from main.views import index, sign_up

urlpatterns = [
    path("", index, name="index"),
    path('sign_up/', sign_up, name='sign_up')
]