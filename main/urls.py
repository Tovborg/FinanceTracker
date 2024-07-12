#main/urls.py

from django.urls import include, path
from main.views import *
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path("", index, name="index"),
    path('sign_up/', sign_up, name='sign_up'),
    path('account/', account_view, name='account'),
    path('account/add_account/', add_account, name='add_account'),
    path('account/update_favorite/', csrf_exempt(updateFavorite), name='update_favorite'),
    path('account/<str:account_name>/', account_details, name='account_details'),
    path('new_transaction/<str:account_name>/', new_transaction, name='new_transaction'),
    path('account/info/<str:account_name>/', account_info, name='account_info'),
]