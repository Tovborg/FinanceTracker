#main/urls.py

from django.urls import include, path
from main.views import *

urlpatterns = [
    path("", index, name="index"),
    path('sign_up/', sign_up, name='sign_up'),
    path('account/', account_view, name='account'),
    path('account/add_account/', add_account, name='add_account'),
]